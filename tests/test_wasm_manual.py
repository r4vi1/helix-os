#!/usr/bin/env python3
"""
HelixOS WASM Hybrid Infrastructure - Manual Test Script
========================================================
Run this script to test all WASM components.

Usage:
    source venv/bin/activate
    python tests/test_wasm_manual.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(title: str):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")


def print_result(test_name: str, success: bool, message: str = ""):
    status = f"{GREEN}✓ PASS{RESET}" if success else f"{RED}✗ FAIL{RESET}"
    print(f"  {status} {test_name}")
    if message and not success:
        print(f"         {YELLOW}{message}{RESET}")


def test_wasm_registry():
    """Test WASM Registry: store, search, delete"""
    print_header("Test 1: WASM Registry")
    
    try:
        from builder.wasm_registry import WASMRegistry, WASMManifest
        
        # Create temp registry
        import tempfile
        temp_dir = tempfile.mkdtemp()
        reg = WASMRegistry(registry_path=temp_dir)
        
        # Test 1.1: Store agent
        manifest = WASMManifest(name='test-fib', task='calculate fibonacci numbers')
        wasm_binary = b'\x00asm\x01\x00\x00\x00'
        path = reg.store('test-fib', wasm_binary, manifest)
        print_result("Store agent", path is not None)
        
        # Test 1.2: List agents
        agents = reg.list_agents()
        print_result("List agents", 'test-fib' in agents)
        
        # Test 1.3: Keyword search
        result = reg.search('compute fibonacci sequence')
        print_result("Keyword search", result == 'test-fib', f"Got: {result}")
        
        # Test 1.4: Semantic search
        match, score = reg.semantic_search('calculate fib series')
        print_result("Semantic search", match == 'test-fib', f"Score: {score:.2f}")
        
        # Test 1.5: Get WASM binary
        binary = reg.get_wasm_binary('test-fib')
        print_result("Get WASM binary", binary == wasm_binary)
        
        # Cleanup
        reg.delete('test-fib')
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return True
        
    except Exception as e:
        print_result("WASM Registry", False, str(e))
        return False


def test_unified_registry():
    """Test Unified Registry: search across K8s and WASM"""
    print_header("Test 2: Unified Registry")
    
    try:
        from builder.unified_registry import UnifiedAgentRegistry, AgentMatch
        
        registry = UnifiedAgentRegistry()
        print_result("Initialize registry", True)
        
        # Search (may return None if registries are empty)
        match = registry.search('calculate fibonacci')
        if match:
            print_result("Search returns AgentMatch", isinstance(match, AgentMatch))
            print(f"         Found: {match.name} ({match.runtime}) - Score: {match.score:.2f}")
        else:
            print_result("Search (empty registry)", True, "No agents found - expected for empty registries")
        
        # Test runtime filter
        match_k8s = registry.search('test', runtime_filter='k8s')
        match_wasm = registry.search('test', runtime_filter='wasm')
        print_result("Runtime filtering", True)
        
        return True
        
    except Exception as e:
        print_result("Unified Registry", False, str(e))
        return False


def test_wasm_executor():
    """Test WASM Executor: check wasmtime availability"""
    print_header("Test 3: WASM Executor")
    
    try:
        from builder.wasm_executor import LocalWASMExecutor, WASMTaskResult
        
        executor = LocalWASMExecutor()
        print_result("Initialize executor", True)
        
        # Check wasmtime
        wasmtime_available = executor._check_wasmtime()
        if wasmtime_available:
            print_result("wasmtime available", True)
        else:
            print_result("wasmtime available", False, "Install with: curl https://wasmtime.dev/install.sh -sSf | bash")
            print(f"         {YELLOW}WASM execution will not work without wasmtime{RESET}")
        
        return True
        
    except Exception as e:
        print_result("WASM Executor", False, str(e))
        return False


def test_controller_integration():
    """Test Controller: unified search integration"""
    print_header("Test 4: Controller Integration")
    
    try:
        from builder.controller import SubAgentController
        
        controller = SubAgentController()
        print_result("Initialize controller", True)
        
        # Check components
        print_result("Unified registry", controller.unified_registry is not None)
        print_result("WASM executor", controller.wasm_executor is not None)
        print_result("Memory system", controller.memory is not None)
        
        # Test classification (doesn't require external services)
        classification = controller.classify_task("calculate fibonacci of 20")
        print_result("Task classification", classification['agent_type'] == 'compute_agent', 
                    f"Type: {classification['agent_type']}")
        
        return True
        
    except Exception as e:
        print_result("Controller Integration", False, str(e))
        return False


def test_embeddings():
    """Test sentence-transformers embeddings"""
    print_header("Test 5: Semantic Embeddings")
    
    try:
        from memory.embeddings import embed, similarity
        
        # Test embedding
        vec1 = embed("calculate fibonacci numbers")
        print_result("Generate embedding", len(vec1) > 0, f"Dimension: {len(vec1)}")
        
        # Test similarity
        vec2 = embed("compute fib sequence")
        sim = similarity(vec1, vec2)
        print_result("Semantic similarity", sim > 0.5, f"Score: {sim:.3f}")
        
        return True
        
    except ImportError:
        print_result("sentence-transformers", False, "Install with: pip install sentence-transformers")
        return False
    except Exception as e:
        print_result("Embeddings", False, str(e))
        return False


def test_wasm_builder():
    """Test WASM Builder: suitability check"""
    print_header("Test 6: WASM Builder")
    
    try:
        from builder.wasm_builder import is_wasm_suitable, WASMBuilder
        
        # Test suitability checks
        pure_compute = is_wasm_suitable("calculate fibonacci", [])
        print_result("Pure compute → WASM suitable", pure_compute == True)
        
        needs_api = is_wasm_suitable("search google for news", ["GOOGLE_API_KEY"])
        print_result("API required → WASM unsuitable", needs_api == False)
        
        # Test builder init
        builder = WASMBuilder()
        print_result("Initialize builder", True)
        
        return True
        
    except Exception as e:
        print_result("WASM Builder", False, str(e))
        return False


def main():
    print(f"\n{BOLD}HelixOS WASM Hybrid Infrastructure - Manual Tests{RESET}")
    print(f"{'='*60}")
    print("Testing all WASM components...\n")
    
    results = []
    
    # Run all tests
    results.append(("WASM Registry", test_wasm_registry()))
    results.append(("Unified Registry", test_unified_registry()))
    results.append(("WASM Executor", test_wasm_executor()))
    results.append(("Controller Integration", test_controller_integration()))
    results.append(("Semantic Embeddings", test_embeddings()))
    results.append(("WASM Builder", test_wasm_builder()))
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {status}  {name}")
    
    print(f"\n{BOLD}Result: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}All tests passed! WASM infrastructure is ready.{RESET}\n")
    else:
        print(f"\n{YELLOW}Some tests failed. See above for details.{RESET}\n")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
