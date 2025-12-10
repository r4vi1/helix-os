"""
Garbage Collection
==================
Cleanup old memories and Docker images.
"""

import subprocess
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import MemoryManager


class MemoryCleanup:
    """
    Garbage collection for old memories and cached Docker images.
    Per Main_idea.md: 30-day retention policy.
    """
    
    DEFAULT_RETENTION_DAYS = 30
    
    def __init__(self, memory_manager: "MemoryManager", retention_days: int = None):
        self.memory = memory_manager
        self.retention_days = retention_days or self.DEFAULT_RETENTION_DAYS
    
    def run_full_cleanup(self) -> dict:
        """Run complete garbage collection."""
        stats = {
            "memories_archived": 0,
            "memories_deleted": 0,
            "docker_images_deleted": 0
        }
        
        # 1. Archive old episodic memories
        stats["memories_archived"] = self._archive_old_memories()
        
        # 2. Delete stale semantic patterns
        stats["memories_deleted"] = self._cleanup_stale_patterns()
        
        # 3. Cleanup unused Docker images
        stats["docker_images_deleted"] = self._cleanup_docker_images()
        
        return stats
    
    def _archive_old_memories(self) -> int:
        """Archive episodic memories not accessed in retention period."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        archived = 0
        
        for memory in self.memory.episodic.get_all():
            if memory.last_accessed < cutoff:
                # Use lifecycle controller to properly archive
                from .lifecycle_controller import MemoryLifecycleController
                controller = MemoryLifecycleController(self.memory)
                controller._archive(memory)
                archived += 1
        
        return archived
    
    def _cleanup_stale_patterns(self) -> int:
        """Delete semantic patterns with poor performance."""
        deleted = 0
        
        for capability in self.memory.semantic.get_all():
            # Delete if:
            # - Low success rate (<50%) AND
            # - Not accessed recently (>30 days)
            cutoff = datetime.now() - timedelta(days=self.retention_days)
            
            if capability.success_rate < 0.5 and capability.last_accessed < cutoff:
                self.memory.semantic.delete(capability.id)
                deleted += 1
        
        return deleted
    
    def _cleanup_docker_images(self) -> int:
        """Remove Docker images not used in retention period."""
        deleted = 0
        
        try:
            # List all helix agent images
            result = subprocess.run(
                ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.CreatedAt}}", 
                 "--filter", "reference=helix-*"],
                capture_output=True, text=True, check=True
            )
            
            cutoff = datetime.now() - timedelta(days=self.retention_days)
            
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                
                parts = line.split("\t")
                if len(parts) != 2:
                    continue
                
                image_name, created_str = parts
                
                # Parse Docker's date format (rough)
                try:
                    # Docker format: "2024-01-15 12:34:56 +0000 UTC"
                    created = datetime.strptime(created_str.split("+")[0].strip(), "%Y-%m-%d %H:%M:%S")
                    
                    if created < cutoff:
                        # Check if used in semantic memory
                        if not self._image_in_use(image_name):
                            subprocess.run(
                                ["docker", "rmi", image_name],
                                capture_output=True, check=True
                            )
                            deleted += 1
                            print(f"[CLEANUP] Deleted Docker image: {image_name}")
                except Exception:
                    continue
                    
        except subprocess.CalledProcessError as e:
            print(f"[WARN] Docker cleanup failed: {e}")
        except FileNotFoundError:
            print("[WARN] Docker not available for cleanup")
        
        return deleted
    
    def _image_in_use(self, image_name: str) -> bool:
        """Check if image is referenced in high-success semantic memory."""
        for memory in self.memory.episodic.get_all():
            if memory.agent_image == image_name and memory.outcome == "success":
                return True
        return False
