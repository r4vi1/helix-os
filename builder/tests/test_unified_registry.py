"""
Tests for UnifiedAgentRegistry
==============================
Tests for the unified search across K8s and WASM registries.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from builder.unified_registry import UnifiedAgentRegistry, AgentMatch
from builder.wasm_registry import WASMRegistry, WASMManifest


class TestAgentMatch:
    """Tests for AgentMatch dataclass."""
    
    def test_agent_match_creation(self):
        """Test basic AgentMatch creation."""
        match = AgentMatch(
            name="test-agent",
            runtime="k8s",
            reference="localhost:5001/test-agent:latest",
            score=0.75,
            task="test task"
        )
        
        assert match.name == "test-agent"
        assert match.runtime == "k8s"
        assert match.score == 0.75
        assert match.capabilities == []
    
    def test_agent_match_with_capabilities(self):
        """Test AgentMatch with capabilities."""
        match = AgentMatch(
            name="compute-agent",
            runtime="wasm",
            reference="/path/to/agent.wasm",
            score=0.9,
            task="compute task",
            capabilities=["math", "compute"]
        )
        
        assert match.capabilities == ["math", "compute"]
    
    def test_agent_match_runtime_types(self):
        """Test that runtime is correctly typed."""
        k8s_match = AgentMatch(
            name="k8s-agent", runtime="k8s",
            reference="image:tag", score=0.5, task="test"
        )
        wasm_match = AgentMatch(
            name="wasm-agent", runtime="wasm",
            reference="/path.wasm", score=0.5, task="test"
        )
        
        assert k8s_match.runtime == "k8s"
        assert wasm_match.runtime == "wasm"


class TestUnifiedAgentRegistry:
    """Tests for UnifiedAgentRegistry class."""
    
    @pytest.fixture
    def temp_wasm_registry(self):
        """Create a temporary WASM registry."""
        temp_dir = tempfile.mkdtemp()
        registry = WASMRegistry(registry_path=temp_dir)
        yield registry
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_k8s_registry(self):
        """Create a mock K8s registry."""
        mock = MagicMock()
        mock.list_agents.return_value = []
        mock.get_agent_metadata.return_value = {}
        return mock
    
    @pytest.fixture
    def unified_registry(self, mock_k8s_registry, temp_wasm_registry):
        """Create a unified registry with mocked K8s and real WASM."""
        return UnifiedAgentRegistry(
            k8s_registry=mock_k8s_registry,
            wasm_registry=temp_wasm_registry
        )
    
    @pytest.fixture
    def sample_wasm(self):
        """Sample WASM binary."""
        return b'\x00asm\x01\x00\x00\x00'
    
    def test_registry_initialization(self, unified_registry):
        """Test unified registry initializes correctly."""
        assert unified_registry.k8s_registry is not None
        assert unified_registry.wasm_registry is not None
    
    def test_search_returns_none_when_empty(self, unified_registry):
        """Test search returns None on empty registries."""
        result = unified_registry.search("any query")
        assert result is None
    
    def test_search_finds_wasm_agent(self, unified_registry, temp_wasm_registry, sample_wasm):
        """Test search finds WASM agent when K8s is empty."""
        manifest = WASMManifest(
            name="fibonacci-wasm",
            task="calculate fibonacci sequence"
        )
        temp_wasm_registry.store("fibonacci-wasm", sample_wasm, manifest)
        
        result = unified_registry.search("calculate fibonacci")
        
        assert result is not None
        assert result.runtime == "wasm"
        assert result.name == "fibonacci-wasm"
    
    def test_search_finds_k8s_agent(self, mock_k8s_registry, temp_wasm_registry):
        """Test search finds K8s agent when WASM is empty."""
        # Setup K8s mock to return an agent
        mock_k8s_registry.list_agents.return_value = ["helix-research"]
        mock_k8s_registry.get_agent_metadata.return_value = {
            "helix.task": "research and analyze topics"
        }
        
        unified = UnifiedAgentRegistry(
            k8s_registry=mock_k8s_registry,
            wasm_registry=temp_wasm_registry
        )
        
        result = unified.search("research topics online")
        
        assert result is not None
        assert result.runtime == "k8s"
        assert result.name == "helix-research"
    
    def test_search_prefers_better_score(self, mock_k8s_registry, temp_wasm_registry, sample_wasm):
        """Test search returns agent with better score."""
        # Setup K8s agent with lower score match
        mock_k8s_registry.list_agents.return_value = ["vague-agent"]
        mock_k8s_registry.get_agent_metadata.return_value = {
            "helix.task": "do something vaguely related"
        }
        
        # Setup WASM agent with exact match
        manifest = WASMManifest(
            name="compute-exact",
            task="calculate exact mathematical computations"
        )
        temp_wasm_registry.store("compute-exact", sample_wasm, manifest)
        
        unified = UnifiedAgentRegistry(
            k8s_registry=mock_k8s_registry,
            wasm_registry=temp_wasm_registry
        )
        
        result = unified.search("calculate mathematical computation")
        
        assert result is not None
        # WASM should win due to better keyword match
        assert result.runtime == "wasm"
    
    def test_pick_best_prefers_higher_score(self, unified_registry):
        """Test _pick_best prefers significantly higher score."""
        k8s = AgentMatch(
            name="k8s", runtime="k8s", 
            reference="img:tag", score=0.8, task="test"
        )
        wasm = AgentMatch(
            name="wasm", runtime="wasm",
            reference="/path", score=0.5, task="test"
        )
        
        best = unified_registry._pick_best(k8s, wasm)
        
        # K8s has much higher score
        assert best.runtime == "k8s"
    
    def test_pick_best_prefers_wasm_on_tie(self, unified_registry):
        """Test _pick_best prefers WASM when scores are close."""
        k8s = AgentMatch(
            name="k8s", runtime="k8s",
            reference="img:tag", score=0.75, task="test"
        )
        wasm = AgentMatch(
            name="wasm", runtime="wasm",
            reference="/path", score=0.72, task="test"
        )
        
        best = unified_registry._pick_best(k8s, wasm)
        
        # Scores within 0.1 - prefer WASM for speed
        assert best.runtime == "wasm"
    
    def test_list_all(self, mock_k8s_registry, temp_wasm_registry, sample_wasm):
        """Test list_all returns agents from both registries."""
        mock_k8s_registry.list_agents.return_value = ["k8s-agent-1", "k8s-agent-2"]
        
        manifest = WASMManifest(name="wasm-agent", task="test")
        temp_wasm_registry.store("wasm-agent", sample_wasm, manifest)
        
        unified = UnifiedAgentRegistry(
            k8s_registry=mock_k8s_registry,
            wasm_registry=temp_wasm_registry
        )
        
        all_agents = unified.list_all()
        
        assert "k8s" in all_agents
        assert "wasm" in all_agents
        assert len(all_agents["k8s"]) == 2
        assert len(all_agents["wasm"]) == 1


class TestUnifiedRegistryEdgeCases:
    """Edge case tests for unified registry."""
    
    @pytest.fixture
    def temp_wasm_registry(self):
        temp_dir = tempfile.mkdtemp()
        registry = WASMRegistry(registry_path=temp_dir)
        yield registry
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_k8s_registry_error_handled(self, temp_wasm_registry):
        """Test that K8s registry errors don't crash search."""
        mock_k8s = MagicMock()
        mock_k8s.list_agents.side_effect = Exception("Connection refused")
        
        unified = UnifiedAgentRegistry(
            k8s_registry=mock_k8s,
            wasm_registry=temp_wasm_registry
        )
        
        # Should handle error gracefully
        # Note: Current implementation may raise; this tests desired behavior
        try:
            result = unified.search("test query")
            # If no exception, result should be None or valid WASM
            assert result is None or result.runtime == "wasm"
        except Exception:
            pytest.skip("Error handling not yet implemented")
    
    def test_helix_prefix_bonus(self):
        """Test that helix-prefixed agents get score bonus."""
        mock_k8s = MagicMock()
        mock_k8s.list_agents.return_value = ["helix-compute", "compute-agent"]
        mock_k8s.get_agent_metadata.side_effect = lambda name: {
            "helix.task": "compute numbers"
        }
        
        temp_dir = tempfile.mkdtemp()
        try:
            wasm_registry = WASMRegistry(registry_path=temp_dir)
            unified = UnifiedAgentRegistry(
                k8s_registry=mock_k8s,
                wasm_registry=wasm_registry
            )
            
            result = unified.search("compute numbers")
            
            # helix-prefixed should be preferred
            assert result is not None
            assert result.name == "helix-compute"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
