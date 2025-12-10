"""
Encrypted Database Connection
=============================
SQLCipher-based encrypted SQLite for privacy-first memory storage.
Uses OS keychain for key management (no plaintext secrets).
"""

import os
import secrets
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

# Try to import sqlcipher, fall back to sqlite3 for development
try:
    import sqlcipher3 as sqlite3
    ENCRYPTION_AVAILABLE = True
except ImportError:
    import sqlite3
    ENCRYPTION_AVAILABLE = False
    print("[WARN] sqlcipher3 not installed. Using unencrypted SQLite.")
    print("       Install with: pip install sqlcipher3-binary")


class EncryptedDatabase:
    """
    Manages encrypted SQLite database connections.
    
    Encryption key is stored in OS keychain:
    - macOS: Keychain Access
    - Linux: Secret Service (GNOME Keyring, KWallet)
    - Windows: Windows Credential Locker
    """
    
    DEFAULT_DB_PATH = "~/.helix/memory.db"
    KEYCHAIN_SERVICE = "helix"
    KEYCHAIN_USERNAME = "memory_key"
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or self.DEFAULT_DB_PATH).expanduser()
        self._ensure_directory()
        self._encryption_key: Optional[str] = None
    
    def _ensure_directory(self):
        """Create database directory if it doesn't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _get_or_create_key(self) -> str:
        """
        Retrieve encryption key from OS keychain, or create if not exists.
        """
        if self._encryption_key:
            return self._encryption_key
        
        try:
            import keyring
            
            # Try to get existing key
            key = keyring.get_password(self.KEYCHAIN_SERVICE, self.KEYCHAIN_USERNAME)
            
            if key is None:
                # Generate new 256-bit key
                key = secrets.token_hex(32)
                keyring.set_password(self.KEYCHAIN_SERVICE, self.KEYCHAIN_USERNAME, key)
                print("[INFO] Generated new encryption key and stored in OS keychain.")
            
            self._encryption_key = key
            return key
            
        except Exception as e:
            # Fallback: use environment variable or generate ephemeral key
            print(f"[WARN] Could not access OS keychain: {e}")
            print("       Using HELIX_MEMORY_KEY environment variable or ephemeral key.")
            
            key = os.environ.get("HELIX_MEMORY_KEY")
            if not key:
                key = secrets.token_hex(32)
                print("[WARN] Using ephemeral key - data will be unreadable after restart!")
            
            self._encryption_key = key
            return key
    
    @contextmanager
    def get_connection(self):
        """
        Get an encrypted database connection.
        
        Usage:
            db = EncryptedDatabase()
            with db.get_connection() as conn:
                conn.execute("SELECT * FROM memories")
        """
        conn = sqlite3.connect(str(self.db_path))
        
        try:
            if ENCRYPTION_AVAILABLE:
                key = self._get_or_create_key()
                # Set encryption key using PRAGMA
                conn.execute(f"PRAGMA key = '{key}'")
                # Verify encryption is working
                conn.execute("SELECT count(*) FROM sqlite_master")
            
            # Enable foreign keys and WAL mode for performance
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            
            yield conn
            conn.commit()
            
        except sqlite3.DatabaseError as e:
            if "file is not a database" in str(e):
                raise RuntimeError(
                    "Database encryption key mismatch. "
                    "The stored key may have changed. "
                    "Check your OS keychain or HELIX_MEMORY_KEY environment variable."
                ) from e
            raise
        finally:
            conn.close()
    
    def initialize_schema(self):
        """Create database tables if they don't exist."""
        with self.get_connection() as conn:
            # Episodic memories table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memories (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    current_tier TEXT DEFAULT 'episodic',
                    
                    raw_task TEXT,
                    refined_task TEXT,
                    task_type TEXT,
                    agent_type TEXT,
                    agent_image TEXT,
                    tools_used TEXT,  -- JSON array
                    
                    outcome TEXT,
                    execution_time_ms INTEGER,
                    error_message TEXT,
                    result_summary TEXT,
                    result_data TEXT,  -- JSON object
                    
                    user_feedback TEXT,
                    user_rating INTEGER,
                    
                    embedding BLOB  -- Serialized float array
                )
            """)
            
            # Semantic memories table (agent capabilities)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memories (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    current_tier TEXT DEFAULT 'semantic',
                    
                    agent_type TEXT UNIQUE,
                    description TEXT,
                    keywords TEXT,  -- JSON array
                    
                    total_executions INTEGER DEFAULT 0,
                    successful_executions INTEGER DEFAULT 0,
                    avg_execution_time_ms REAL DEFAULT 0.0,
                    
                    common_tools TEXT,  -- JSON array
                    task_patterns TEXT,  -- JSON array
                    
                    embedding BLOB
                )
            """)
            
            # User preferences table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    
                    preference_type TEXT,
                    preference_value TEXT,
                    confidence REAL DEFAULT 0.5,
                    source_task_ids TEXT,  -- JSON array
                    
                    UNIQUE(preference_type, preference_value)
                )
            """)
            
            # Archive table for old episodic memories
            conn.execute("""
                CREATE TABLE IF NOT EXISTS archived_memories (
                    id TEXT PRIMARY KEY,
                    original_table TEXT,
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    compressed_data BLOB  -- Compressed JSON
                )
            """)
            
            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_task_type 
                ON episodic_memories(task_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_outcome 
                ON episodic_memories(outcome)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_last_accessed 
                ON episodic_memories(last_accessed)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_agent_type 
                ON semantic_memories(agent_type)
            """)
            
            print("[INFO] Database schema initialized.")
    
    def is_encrypted(self) -> bool:
        """Check if database encryption is available and active."""
        return ENCRYPTION_AVAILABLE


# Singleton instance for convenience
_default_db: Optional[EncryptedDatabase] = None


def get_database(db_path: Optional[str] = None) -> EncryptedDatabase:
    """Get or create the default database instance."""
    global _default_db
    if _default_db is None or db_path is not None:
        _default_db = EncryptedDatabase(db_path)
    return _default_db
