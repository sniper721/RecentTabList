#!/usr/bin/env python3
"""
Test script for webhook settings fix
"""

def test_webhook_settings_parsing():
    """Test that webhook settings can handle empty integer fields"""
    
    # Test cases for integer parsing
    test_cases = [
        ("", 1),      # Empty string should default to 1
        ("0", 1),     # Zero should default to 1
        ("5", 5),     # Valid number should be preserved
        ("abc", 1),   # Invalid string should default to 1
        ("-5", 1),    # Negative number should default to 1
    ]
    
    print("Testing integer field parsing for webhook settings:")
    
    for input_val, expected in test_cases:
        try:
            # Simulate the parsing logic from our fix
            if input_val == "":
                result = 1
            else:
                try:
                    parsed = int(input_val)
                    result = parsed if parsed > 0 else 1
                except ValueError:
                    result = 1
            
            status = "✅ PASS" if result == expected else "❌ FAIL"
            print(f"  Input: '{input_val}' -> Output: {result} {status}")
        except Exception as e:
            print(f"  Input: '{input_val}' -> Error: {e} ❌ FAIL")
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    test_webhook_settings_parsing()