"""
Tests for WASMBuilder
=====================
Tests for WASM compilation and building.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from builder.wasm_builder import WASMBuilder, is_wasm_suitable
from builder.wasm_registry import WASMRegistry, WASMManifest


class TestIsWasmSuitable:
    """Tests for the is_wasm_suitable function."""
    
    def test_compute_task_no_apis_is_suitable(self):
        """Pure compute tasks without APIs should be WASM suitable."""
        assert is_wasm_suitable("calculate fibonacci sequence", []) is True
        assert is_wasm_suitable("compute prime numbers", []) is True
        assert is_wasm_suitable("sum these numbers", []) is True
    
    def test_task_with_apis_not_suitable(self):
        """Tasks requiring APIs should not be WASM suitable."""
        assert is_wasm_suitable("research topic", ["GOOGLE_SEARCH_API_KEY"]) is False
        assert is_wasm_suitable("call gemini", ["GEMINI_API_KEY"]) is False
    
    def test_http_keywords_not_suitable(self):
        """Tasks with HTTP-related keywords should not be WASM suitable."""
        assert is_wasm_suitable("fetch data from api", []) is False
        assert is_wasm_suitable("make http request", []) is False
        assert is_wasm_suitable("download file", []) is False
    
    def test_storage_keywords_not_suitable(self):
        """Tasks needing storage should not be WASM suitable."""
        assert is_wasm_suitable("save to database", []) is False
        assert is_wasm_suitable("persist data", []) is False
        assert is_wasm_suitable("store in file", []) is False
    
    def test_auth_keywords_not_suitable(self):
        """Tasks needing authentication should not be WASM suitable."""
        assert is_wasm_suitable("authenticate user", []) is False
        assert is_wasm_suitable("use token to access", []) is False
        assert is_wasm_suitable("credential validation", []) is False
    
    def test_transform_keywords_suitable(self):
        """Data transformation tasks should be WASM suitable."""
        assert is_wasm_suitable("parse json data", []) is True
        assert is_wasm_suitable("transform format", []) is True
        assert is_wasm_suitable("convert encoding", []) is True
    
    def test_analysis_keywords_suitable(self):
        """Analysis tasks should be WASM suitable."""
        assert is_wasm_suitable("analyze text content", []) is True
        assert is_wasm_suitable("process data", []) is True
        assert is_wasm_suitable("filter results", []) is True
    
    def test_ambiguous_defaults_to_not_suitable(self):
        """Ambiguous tasks should default to not suitable (safer)."""
        assert is_wasm_suitable("do something", []) is False
        assert is_wasm_suitable("handle task", []) is False


class TestWASMManifestCreation:
    """Tests for manifest creation in builder."""
    
    def test_manifest_from_builder_params(self):
        """Test that builder creates correct manifest."""
        manifest = WASMManifest(
            name="test-builder",
            task="test task description",
            capabilities=["compute", "test"],
            runtime="wasm"
        )
        
        assert manifest.name == "test-builder"
        assert manifest.task == "test task description"
        assert manifest.runtime == "wasm"
        assert "compute" in manifest.capabilities


class TestWASMBuilder:
    """Tests for WASMBuilder class."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry for testing."""
        temp_dir = tempfile.mkdtemp()
        registry = WASMRegistry(registry_path=temp_dir)
        yield registry
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def builder(self, temp_registry):
        """Create a builder with temp registry."""
        return WASMBuilder(registry=temp_registry)
    
    def test_builder_initialization(self, builder):
        """Test builder initializes correctly."""
        assert builder.registry is not None
    
    def test_verify_valid_wasm(self, builder, temp_registry):
        """Test verification of valid WASM binary."""
        # Create a valid WASM binary (magic bytes)
        valid_wasm = b'\x00asm\x01\x00\x00\x00'
        manifest = WASMManifest(name="valid", task="test")
        temp_registry.store("valid", valid_wasm, manifest)
        
        assert builder.verify("valid") is True
    
    def test_verify_invalid_wasm(self, builder, temp_registry):
        """Test verification fails for invalid WASM."""
        # Create an invalid binary (wrong magic bytes)
        invalid_wasm = b'not a wasm file'
        manifest = WASMManifest(name="invalid", task="test")
        temp_registry.store("invalid", invalid_wasm, manifest)
        
        assert builder.verify("invalid") is False
    
    def test_verify_nonexistent_agent(self, builder):
        """Test verification fails for non-existent agent."""
        assert builder.verify("does-not-exist") is False
    
    def test_verify_empty_binary(self, builder, temp_registry):
        """Test verification fails for too-small binary."""
        # Only 2 bytes, too small
        tiny_wasm = b'\x00a'
        manifest = WASMManifest(name="tiny", task="test")
        temp_registry.store("tiny", tiny_wasm, manifest)
        
        assert builder.verify("tiny") is False


class TestWASMBuilderCompilation:
    """Tests for actual WASM compilation (may skip if Docker unavailable)."""
    
    @pytest.fixture
    def temp_registry(self):
        temp_dir = tempfile.mkdtemp()
        registry = WASMRegistry(registry_path=temp_dir)
        yield registry
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def builder(self, temp_registry):
        return WASMBuilder(registry=temp_registry)
    
    @pytest.fixture
    def simple_go_code(self):
        """Simple Go program that compiles to WASM."""
        return '''
package main

import "fmt"

func main() {
    fmt.Println(`{"result": "hello from wasm"}`)
}
'''
    
    @pytest.mark.skipif(
        not shutil.which("docker"),
        reason="Docker not available"
    )
    def test_compile_simple_program(self, builder, simple_go_code):
        """Test compilation of simple Go program to WASM."""
        wasm_binary = builder.compile(simple_go_code)
        
        # Should have WASM magic bytes
        assert wasm_binary[:4] == b'\x00asm'
        # Should be reasonably sized
        assert len(wasm_binary) > 100
    
    @pytest.mark.skipif(
        not shutil.which("docker"),
        reason="Docker not available"
    )
    def test_build_and_register(self, builder, simple_go_code, temp_registry):
        """Test full build and register flow."""
        path = builder.build_and_register(
            source_code=simple_go_code,
            agent_name="hello-wasm",
            task_description="print hello message",
            capabilities=["demo"]
        )
        
        assert path is not None
        assert Path(path).exists()
        assert "hello-wasm" in temp_registry.list_agents()
        
        # Verify the stored WASM is valid
        assert builder.verify("hello-wasm") is True
    
    @pytest.mark.skipif(
        not shutil.which("go"),
        reason="Go not available"
    )
    def test_compile_native(self, builder, simple_go_code):
        """Test native compilation (without Docker)."""
        try:
            wasm_binary = builder.compile_native(simple_go_code)
            
            # Should have WASM magic bytes
            assert wasm_binary[:4] == b'\x00asm'
        except Exception as e:
            # If GOOS=wasip1 not supported, skip
            if "unsupported" in str(e).lower():
                pytest.skip("WASI target not supported by this Go version")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
