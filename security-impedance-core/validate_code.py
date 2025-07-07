#!/usr/bin/env python3
"""
Comprehensive code validation for security-impedance-core
"""

import sys
import time
sys.path.insert(0, 'src')

def test_all_modules():
    """Test all security impedance modules"""
    print('=== SECURITY IMPEDANCE VALIDATION ===\n')
    
    try:
        # Test alias module
        print('Testing impedance.alias...')
        from impedance.alias import alias_path, is_alias
        
        # Test deterministic aliasing
        alias1 = alias_path('/test/path.txt')
        alias2 = alias_path('/test/path.txt')
        assert alias1 == alias2, "Aliasing should be deterministic"
        assert alias1.startswith('FILE_'), "Alias should start with FILE_"
        assert len(alias1) == 13, "Alias should be 13 characters"
        assert is_alias(alias1), "Should recognize valid alias"
        assert not is_alias('/real/path.txt'), "Should reject real paths"
        print('✅ alias.py - All tests passed')
        
        # Test padding module
        print('\nTesting impedance.padding...')
        from impedance.padding import pad, PROMPT_PAD_TOKENS
        
        padded, added = pad('hello', 10)
        assert len(padded) == 10, "Should pad to exact length"
        assert added == 5, "Should report correct padding added"
        assert PROMPT_PAD_TOKENS == 4096, "Default should be 4096"
        print('✅ padding.py - All tests passed')
        
        # Test scan module
        print('\nTesting impedance.scan...')
        from impedance.scan import contains_secret, contains_raw_path
        
        assert contains_secret('sk_live_1234567890abcdef1234'), "Should detect Stripe live key"
        assert contains_secret('sk_test_1234567890abcdef1234'), "Should detect Stripe test key"
        assert contains_secret('AKIA1234567890ABCDEF'), "Should detect AWS key"
        assert not contains_secret('normal text'), "Should not flag normal text"
        
        assert contains_raw_path('/etc/passwd'), "Should detect raw paths"
        assert not contains_raw_path('FILE_a1b2c3d4'), "Should allow aliased paths"
        print('✅ scan.py - All tests passed')
        
        # Performance test
        print('\nTesting performance...')
        start = time.perf_counter()
        
        # Combined operation
        text = "Check /var/log/app.log"
        has_path = contains_raw_path(text)
        if has_path:
            alias = alias_path('/var/log/app.log')
        padded, _ = pad(text, 100)
        
        elapsed = time.perf_counter() - start
        assert elapsed < 0.001, f"Should be under 1ms, was {elapsed*1000:.3f}ms"
        print(f'✅ Performance test passed - {elapsed*1000:.3f}ms')
        
        print('\n🎉 ALL TESTS PASSED!')
        print('📊 Security impedance core validated successfully')
        return True
        
    except Exception as e:
        print(f'\n❌ VALIDATION FAILED: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_all_modules()
    sys.exit(0 if success else 1)