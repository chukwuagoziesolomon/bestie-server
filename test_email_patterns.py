#!/usr/bin/env python3
"""
Test email detection with the fixed regex patterns
"""
import re

def test_email_patterns():
    """Test both old and new email detection patterns"""
    
    test_cases = [
        "chukwuagoziesolomon@gmail.com",
        "  chukwuagoziesolomon@gmail.com  ",
        "My email is chukwuagoziesolomon@gmail.com",
        "hello",
        "hi there",
        "chukwuagoziesolomon@gmail.com please",
    ]
    
    # Old pattern (problematic)
    old_pattern = r"[^@\s]+@[^@\s]+\.[^@\s]+"
    
    # New pattern (consistent)
    new_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    
    print("=== EMAIL PATTERN COMPARISON ===")
    print(f"Old pattern (re.match): {old_pattern}")
    print(f"New pattern (re.search): {new_pattern}")
    print()
    
    for test_case in test_cases:
        print(f"Testing: '{test_case}'")
        
        # Old method
        old_match = re.match(old_pattern, test_case)
        if old_match:
            print(f"  OLD (match): ✅ Found '{old_match.group()}'")
        else:
            print(f"  OLD (match): ❌ No match")
        
        # New method
        new_match = re.search(new_pattern, test_case)
        if new_match:
            print(f"  NEW (search): ✅ Found '{new_match.group()}'")
        else:
            print(f"  NEW (search): ❌ No match")
            
        print()
    
    print("=== ANALYSIS ===")
    print("The NEW pattern with re.search() should detect emails anywhere in the message")
    print("The OLD pattern with re.match() only detects emails at the start of the message")

if __name__ == '__main__':
    test_email_patterns()