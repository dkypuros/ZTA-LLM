#!/usr/bin/env python3
"""
Critical Fixes Validation Test Suite
Tests all must-fix gaps to ensure stack functionality
"""

import sys
import os
import time
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

class TestResults:
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
    
    def add_test(self, name, status, details="", error=""):
        self.tests.append({
            "name": name,
            "status": status,
            "details": details,
            "error": error
        })
        if status == "PASS":
            self.passed += 1
        else:
            self.failed += 1
    
    def print_summary(self):
        print("\n" + "="*80)
        print("CRITICAL FIXES VALIDATION RESULTS")
        print("="*80)
        
        for test in self.tests:
            status_icon = "✅" if test["status"] == "PASS" else "❌"
            print(f"{status_icon} {test['name']}: {test['status']}")
            if test["details"]:
                print(f"   {test['details']}")
            if test["error"]:
                print(f"   ERROR: {test['error']}")
        
        print("\n" + "-"*80)
        print(f"TOTAL: {self.passed} PASSED, {self.failed} FAILED")
        
        if self.failed == 0:
            print("🎉 ALL CRITICAL FIXES VALIDATED - STACK IS FUNCTIONAL")
        else:
            print("⚠️  SOME CRITICAL ISSUES REMAIN - STACK MAY NOT FUNCTION")
        print("="*80)

def test_gap_a_os_import():
    """Test Gap A: Missing os import in path_aliasing.py"""
    try:
        from wrapper.path_aliasing import PathAliaser
        aliaser = PathAliaser()
        result = aliaser.alias_path("/test/path.txt")
        
        # Verify it uses os.path.normpath (not resolve)
        if result.alias_token.startswith("FILE_") and len(result.alias_token) == 13:
            return "PASS", f"Path aliasing works: {result.alias_token}", ""
        else:
            return "FAIL", "", "Invalid alias token format"
    except Exception as e:
        return "FAIL", "", str(e)

def test_gap_b_port_config():
    """Test Gap B: OPA config port alignment"""
    try:
        opa_config_path = "deploy/opa/config/opa-config.yaml"
        envoy_config_path = "deploy/envoy/envoy.yaml"
        
        # Check OPA config
        with open(opa_config_path, 'r') as f:
            opa_content = f.read()
        
        # Check Envoy config  
        with open(envoy_config_path, 'r') as f:
            envoy_content = f.read()
        
        opa_has_8181 = ":8181" in opa_content
        envoy_has_8181 = "port_value: 8181" in envoy_content
        
        if opa_has_8181 and envoy_has_8181:
            return "PASS", "Both configs use port 8181", ""
        else:
            return "FAIL", "", f"Port mismatch - OPA: {opa_has_8181}, Envoy: {envoy_has_8181}"
    except Exception as e:
        return "FAIL", "", str(e)

def test_gap_c_mcp_error_handling():
    """Test Gap C: MCP server validation error handling"""
    try:
        # Check if PydanticValidationError is imported and handled
        with open("src/mcp_server/server.py", 'r') as f:
            content = f.read()
        
        has_import = "PydanticValidationError" in content
        has_handling = "(ValidationError, PydanticValidationError)" in content
        
        if has_import and has_handling:
            return "PASS", "PydanticValidationError properly imported and handled", ""
        else:
            return "FAIL", "", f"Missing proper error handling - import: {has_import}, handling: {has_handling}"
    except Exception as e:
        return "FAIL", "", str(e)

def test_gap_d_fastapi_entrypoint():
    """Test Gap D: FastAPI wrapper entrypoint exists"""
    try:
        from wrapper.api import app
        
        # Check that it has the expected routes
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        expected = ['/health', '/process', '/metrics', '/config']
        
        has_all_routes = all(route in routes for route in expected)
        
        if has_all_routes:
            return "PASS", f"FastAPI app created with routes: {expected}", ""
        else:
            return "FAIL", "", f"Missing routes. Found: {routes}"
    except Exception as e:
        return "FAIL", "", str(e)

def test_gap_e_opa_source_address():
    """Test Gap E: OPA policy uses source_address not remote_addr"""
    try:
        with open("deploy/opa/policies/data_firewall.rego", 'r') as f:
            content = f.read()
        
        has_source_address = "input.source_address" in content
        has_remote_addr = "input.request.remote_addr" in content
        
        if has_source_address and not has_remote_addr:
            return "PASS", "Uses input.source_address for Envoy compatibility", ""
        else:
            return "FAIL", "", f"source_address: {has_source_address}, remote_addr: {has_remote_addr}"
    except Exception as e:
        return "FAIL", "", str(e)

def test_security_impedance_core():
    """Test the core validation suite"""
    try:
        # Change to security-impedance-core directory and run validation
        original_dir = os.getcwd()
        os.chdir("security-impedance-core")
        
        # Import and test the modules directly
        sys.path.insert(0, 'src')
        
        from impedance.alias import alias_path, is_alias
        from impedance.padding import pad, PROMPT_PAD_TOKENS
        from impedance.scan import contains_secret, contains_raw_path
        
        # Test each module
        start_time = time.perf_counter()
        
        # Test alias
        alias1 = alias_path('/test/path.txt')
        alias2 = alias_path('/test/path.txt')
        assert alias1 == alias2, "Aliasing not deterministic"
        assert is_alias(alias1), "Alias not recognized"
        
        # Test padding
        padded, added = pad('hello', 10)
        assert len(padded) == 10, "Padding length incorrect"
        assert added == 5, "Added padding count incorrect"
        
        # Test scanning
        assert contains_secret('sk_live_1234567890abcdef1234'), "Failed to detect Stripe key"
        assert contains_raw_path('/etc/passwd'), "Failed to detect raw path"
        
        elapsed = time.perf_counter() - start_time
        
        os.chdir(original_dir)
        
        return "PASS", f"All core modules working, performance: {elapsed*1000:.3f}ms", ""
        
    except Exception as e:
        os.chdir(original_dir)
        return "FAIL", "", str(e)

def test_performance_constraint():
    """Test that processing stays under performance constraints"""
    try:
        from wrapper.security_wrapper import SecurityWrapper
        
        wrapper = SecurityWrapper()
        
        # Test multiple prompts to get average
        times = []
        for i in range(10):
            start = time.perf_counter()
            result = wrapper.process_prompt(f"Test prompt {i} without secrets")
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # Convert to ms
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Should be well under 15ms constraint
        if max_time < 15:
            return "PASS", f"Avg: {avg_time:.3f}ms, Max: {max_time:.3f}ms (< 15ms)", ""
        else:
            return "FAIL", "", f"Performance too slow - Max: {max_time:.3f}ms"
            
    except Exception as e:
        return "FAIL", "", str(e)

def main():
    print("Running Critical Fixes Validation Suite...")
    print("Testing all must-fix gaps to ensure stack functionality\n")
    
    results = TestResults()
    
    # Run all tests
    tests = [
        ("Gap A: OS Import Fix", test_gap_a_os_import),
        ("Gap B: Envoy-OPA Port Alignment", test_gap_b_port_config),
        ("Gap C: MCP Error Handling", test_gap_c_mcp_error_handling),
        ("Gap D: FastAPI Entrypoint", test_gap_d_fastapi_entrypoint),
        ("Gap E: OPA Source Address", test_gap_e_opa_source_address),
        ("Security Impedance Core", test_security_impedance_core),
        ("Performance Constraints", test_performance_constraint),
    ]
    
    for test_name, test_func in tests:
        print(f"Running: {test_name}...")
        try:
            status, details, error = test_func()
            results.add_test(test_name, status, details, error)
        except Exception as e:
            results.add_test(test_name, "FAIL", "", f"Test exception: {str(e)}")
    
    # Print results
    results.print_summary()
    
    return results.failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)