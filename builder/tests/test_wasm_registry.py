"""
Tests for WASMRegistry
======================
Comprehensive tests for the WASM module registry.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from builder.wasm_registry import WASMRegistry, WASMManifest


class TestWASMManifest:
    """Tests for WASMManifest dataclass."""
    
    def test_manifest_creation(self):
        """Test basic manifest creation."""
        manifest = WASMManifest(
            name="test-agent",
            task="calculate fibonacci"
        )
        
        assert manifest.name == "test-agent"
        assert manifest.task == "calculate fibonacci"
        assert manifest.runtime == "wasm"
        assert manifest.capabilities == []
        assert manifest.wasm_file == "agent.wasm"
        assert manifest.created is not None
    
    def test_manifest_with_capabilities(self):
        """Test manifest with capabilities list."""
        manifest = WASMManifest(
            name="compute-agent",
            task="perform calculations",
            capabilities=["math", "compute"]
        )
        
        assert manifest.capabilities == ["math", "compute"]
    
    def test_manifest_custom_wasm_file(self):
        """Test manifest with custom wasm filename."""
        manifest = WASMManifest(
            name="custom",
            task="custom task",
            wasm_file="custom.wasm"
        )
        
        assert manifest.wasm_file == "custom.wasm"


class TestWASMRegistry:
    """Tests for WASMRegistry class."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry for testing."""
        temp_dir = tempfile.mkdtemp()
        registry = WASMRegistry(registry_path=temp_dir)
        yield registry
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def sample_wasm_binary(self):
        """Create a minimal valid WASM binary (magic bytes + version)."""
        # WASM magic: \0asm
        # Version: 1 (little endian)
        return b'\x00asm\x01\x00\x00\x00'
    
    def test_registry_initialization(self, temp_registry):
        """Test registry creates directory on init."""
        assert temp_registry.registry_path.exists()
        assert temp_registry.registry_path.is_dir()
    
    def test_list_agents_empty(self, temp_registry):
        """Test listing agents on empty registry."""
        agents = temp_registry.list_agents()
        assert agents == []
    
    def test_store_and_list(self, temp_registry, sample_wasm_binary):
        """Test storing an agent and listing it."""
        manifest = WASMManifest(
            name="fibonacci",
            task="calculate fibonacci sequence"
        )
        
        path = temp_registry.store("fibonacci", sample_wasm_binary, manifest)
        
        assert path is not None
        assert Path(path).exists()
        
        agents = temp_registry.list_agents()
        assert "fibonacci" in agents
    
    def test_store_multiple_agents(self, temp_registry, sample_wasm_binary):
        """Test storing multiple agents."""
        for name in ["agent-a", "agent-b", "agent-c"]:
            manifest = WASMManifest(name=name, task=f"task for {name}")
            temp_registry.store(name, sample_wasm_binary, manifest)
        
        agents = temp_registry.list_agents()
        assert len(agents) == 3
        assert set(agents) == {"agent-a", "agent-b", "agent-c"}
    
    def test_get_agent_metadata(self, temp_registry, sample_wasm_binary):
        """Test retrieving agent metadata."""
        manifest = WASMManifest(
            name="metadata-test",
            task="test metadata retrieval",
            capabilities=["test", "demo"]
        )
        temp_registry.store("metadata-test", sample_wasm_binary, manifest)
        
        metadata = temp_registry.get_agent_metadata("metadata-test")
        
        assert metadata["helix.task"] == "test metadata retrieval"
        assert metadata["helix.runtime"] == "wasm"
        assert "test" in metadata["helix.capabilities"]
    
    def test_get_metadata_nonexistent(self, temp_registry):
        """Test getting metadata for non-existent agent."""
        metadata = temp_registry.get_agent_metadata("does-not-exist")
        assert metadata == {}
    
    def test_get_manifest(self, temp_registry, sample_wasm_binary):
        """Test retrieving full manifest object."""
        original = WASMManifest(
            name="manifest-test",
            task="test manifest",
            capabilities=["cap1", "cap2"]
        )
        temp_registry.store("manifest-test", sample_wasm_binary, original)
        
        retrieved = temp_registry.get_manifest("manifest-test")
        
        assert retrieved is not None
        assert retrieved.name == original.name
        assert retrieved.task == original.task
        assert retrieved.capabilities == original.capabilities
    
    def test_get_wasm_path(self, temp_registry, sample_wasm_binary):
        """Test getting path to WASM binary."""
        manifest = WASMManifest(name="path-test", task="test")
        temp_registry.store("path-test", sample_wasm_binary, manifest)
        
        path = temp_registry.get_wasm_path("path-test")
        
        assert path is not None
        assert path.exists()
        assert path.name == "agent.wasm"
    
    def test_get_wasm_binary(self, temp_registry, sample_wasm_binary):
        """Test retrieving WASM binary content."""
        manifest = WASMManifest(name="binary-test", task="test")
        temp_registry.store("binary-test", sample_wasm_binary, manifest)
        
        binary = temp_registry.get_wasm_binary("binary-test")
        
        assert binary == sample_wasm_binary
    
    def test_delete_agent(self, temp_registry, sample_wasm_binary):
        """Test deleting an agent."""
        manifest = WASMManifest(name="delete-me", task="test")
        temp_registry.store("delete-me", sample_wasm_binary, manifest)
        
        assert "delete-me" in temp_registry.list_agents()
        
        result = temp_registry.delete("delete-me")
        
        assert result is True
        assert "delete-me" not in temp_registry.list_agents()
    
    def test_delete_nonexistent(self, temp_registry):
        """Test deleting non-existent agent."""
        result = temp_registry.delete("does-not-exist")
        assert result is False
    
    def test_search_exact_match(self, temp_registry, sample_wasm_binary):
        """Test search finds exact task match."""
        manifest = WASMManifest(
            name="fibonacci-agent",
            task="calculate fibonacci sequence"
        )
        temp_registry.store("fibonacci-agent", sample_wasm_binary, manifest)
        
        result = temp_registry.search("calculate fibonacci sequence")
        
        assert result == "fibonacci-agent"
    
    def test_search_partial_match(self, temp_registry, sample_wasm_binary):
        """Test search finds partial keyword match with stemming."""
        manifest = WASMManifest(
            name="math-compute",
            task="perform mathematical calculations and computations"
        )
        temp_registry.store("math-compute", sample_wasm_binary, manifest)
        
        # Should match because: calculate -> calcul, calculations -> calcul
        result = temp_registry.search("calculate math problem")
        
        assert result == "math-compute"
    
    def test_search_no_match(self, temp_registry, sample_wasm_binary):
        """Test search returns None when no match."""
        manifest = WASMManifest(name="agent", task="do something specific")
        temp_registry.store("agent", sample_wasm_binary, manifest)
        
        result = temp_registry.search("completely unrelated query")
        
        assert result is None
    
    def test_search_empty_registry(self, temp_registry):
        """Test search on empty registry."""
        result = temp_registry.search("any query")
        assert result is None
    
    def test_search_best_match(self, temp_registry, sample_wasm_binary):
        """Test search returns best match when multiple candidates."""
        agents = [
            ("agent-a", "process text data"),
            ("agent-b", "analyze text and generate report"),
            ("agent-c", "calculate numbers")
        ]
        
        for name, task in agents:
            manifest = WASMManifest(name=name, task=task)
            temp_registry.store(name, sample_wasm_binary, manifest)
        
        result = temp_registry.search("analyze and process text")
        
        # Should match agent-a or agent-b (both have "text")
        assert result in ["agent-a", "agent-b"]


class TestWASMRegistryEdgeCases:
    """Edge case tests for WASMRegistry."""
    
    @pytest.fixture
    def temp_registry(self):
        temp_dir = tempfile.mkdtemp()
        registry = WASMRegistry(registry_path=temp_dir)
        yield registry
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_overwrite_existing_agent(self, temp_registry):
        """Test overwriting an existing agent."""
        binary_v1 = b'\x00asm\x01\x00\x00\x00'
        binary_v2 = b'\x00asm\x01\x00\x00\x00\x00\x00'  # Slightly different
        
        manifest = WASMManifest(name="versioned", task="v1 task")
        temp_registry.store("versioned", binary_v1, manifest)
        
        # Overwrite with new version
        manifest2 = WASMManifest(name="versioned", task="v2 task updated")
        temp_registry.store("versioned", binary_v2, manifest2)
        
        # Should only have one agent
        assert len(temp_registry.list_agents()) == 1
        
        # Should have new metadata
        metadata = temp_registry.get_agent_metadata("versioned")
        assert metadata["helix.task"] == "v2 task updated"
        
        # Should have new binary
        binary = temp_registry.get_wasm_binary("versioned")
        assert binary == binary_v2
    
    def test_special_characters_in_task(self, temp_registry):
        """Test handling of special characters in task description."""
        binary = b'\x00asm\x01\x00\x00\x00'
        manifest = WASMManifest(
            name="special",
            task="calculate x^2 + y^2 = r^2 (circle equation)"
        )
        temp_registry.store("special", binary, manifest)
        
        metadata = temp_registry.get_agent_metadata("special")
        assert "circle" in metadata["helix.task"]
    
    def test_unicode_in_task(self, temp_registry):
        """Test handling of unicode in task description."""
        binary = b'\x00asm\x01\x00\x00\x00'
        manifest = WASMManifest(
            name="unicode",
            task="计算 fibonacci 数列"  # Chinese characters
        )
        temp_registry.store("unicode", binary, manifest)
        
        metadata = temp_registry.get_agent_metadata("unicode")
        assert "fibonacci" in metadata["helix.task"]


class TestStemming:
    """Tests for the stemming functionality."""
    
    def test_stem_basic_suffixes(self):
        """Test basic suffix removal."""
        from builder.wasm_registry import WASMRegistry
        
        # -ing (via compound suffix)
        assert WASMRegistry._stem("running") == "runn"
        assert WASMRegistry._stem("calculating") == "calcul"  # ating suffix
        
        # -ed
        assert WASMRegistry._stem("computed") == "comput"
        
        # -s (plurals)
        assert WASMRegistry._stem("numbers") == "number"
        
        # -ation (compound suffix)
        assert WASMRegistry._stem("calculation") == "calcul"
        
        # -ical
        assert WASMRegistry._stem("mathematical") == "mathemat"
    
    def test_stem_preserves_short_words(self):
        """Test that short words are not over-stemmed."""
        from builder.wasm_registry import WASMRegistry
        
        # Words that would become too short (< 3 chars) should be preserved
        assert WASMRegistry._stem("the") == "the"
        assert WASMRegistry._stem("as") == "as"
    
    def test_stem_matching_works(self):
        """Test that stemming enables matching of related words."""
        from builder.wasm_registry import WASMRegistry
        
        # These pairs should produce the same stem
        assert WASMRegistry._stem("calculate") == WASMRegistry._stem("calculating")
        assert WASMRegistry._stem("compute") == WASMRegistry._stem("computed")
        assert WASMRegistry._stem("analyze") == WASMRegistry._stem("analyzing")


class TestSemanticSearch:
    """Tests for semantic search functionality."""
    
    @pytest.fixture
    def temp_registry(self):
        temp_dir = tempfile.mkdtemp()
        registry = WASMRegistry(registry_path=temp_dir)
        yield registry
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def sample_wasm(self):
        return b'\x00asm\x01\x00\x00\x00'
    
    def test_semantic_search_with_alpha_1_is_keyword_only(self, temp_registry, sample_wasm):
        """Test that alpha=1.0 produces keyword-only search."""
        manifest = WASMManifest(
            name="math-agent",
            task="calculate mathematical operations"
        )
        temp_registry.store("math-agent", sample_wasm, manifest)
        
        # alpha=1.0 should use only keywords
        result, score = temp_registry.semantic_search(
            "calculate math problem", 
            alpha=1.0
        )
        
        assert result == "math-agent"
        assert score > 0
    
    def test_semantic_search_returns_tuple(self, temp_registry, sample_wasm):
        """Test that semantic_search returns (name, score) tuple."""
        manifest = WASMManifest(name="test", task="test task")
        temp_registry.store("test", sample_wasm, manifest)
        
        result = temp_registry.semantic_search("test task")
        
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_semantic_search_empty_registry(self, temp_registry):
        """Test semantic search on empty registry."""
        result, score = temp_registry.semantic_search("any query")
        assert result is None
        assert score == 0.0
    
    def test_semantic_search_finds_conceptual_match(self, temp_registry, sample_wasm):
        """Test that semantic search can find conceptually related tasks."""
        # Store an agent with specific terminology
        manifest = WASMManifest(
            name="fibonacci-generator",
            task="generate fibonacci number sequence"
        )
        temp_registry.store("fibonacci-generator", sample_wasm, manifest)
        
        # Search with different but related terminology
        # With alpha=0.5, semantic component should help
        result, score = temp_registry.semantic_search(
            "calculate fibonacci series",
            alpha=0.5
        )
        
        # Should still find the agent (fibonacci matches)
        assert result == "fibonacci-generator"
    
    def test_store_with_embedding(self, temp_registry, sample_wasm):
        """Test storing agent with pre-computed embedding."""
        manifest = WASMManifest(
            name="embedded-agent",
            task="perform calculations"
        )
        
        # store_with_embedding should work even if embeddings unavailable
        path = temp_registry.store_with_embedding(
            "embedded-agent", 
            sample_wasm, 
            manifest
        )
        
        assert path is not None
        assert "embedded-agent" in temp_registry.list_agents()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
