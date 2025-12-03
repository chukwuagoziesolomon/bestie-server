#!/usr/bin/env python3
"""
Test email regex pattern used in WhatsApp views
"""
import re

def test_email_regex():
    print("TESTING EMAIL REGEX PATTERN")
    print("=" * 40)
    
    # This is the exact regex from the WhatsApp views
    email_pattern = r"[^@\s]+@[^@\s]+\.[^@\s]+"
    
    test_emails = [
        "user@gmail.com",
        "test.user@yahoo.com",
        "example@example.com",
        "user+tag@domain.co.uk",
        "simple@test.org",
        "user123@domain123.com",
        "hello@world.info",
        "contact@business.net",
        "admin@company.co",
        "test@test.test"
    ]
    
    print("Testing valid emails:")
    for email in test_emails:
        match = re.match(email_pattern, email)
        if match:
            print(f"✅ {email} - MATCHED")
        else:
            print(f"❌ {email} - NO MATCH")
    
    print("\nTesting invalid inputs:")
    invalid_inputs = [
        "not an email",
        "@domain.com",
        "user@",
        "user@domain",
        "user domain.com",
        "hello world",
        "",
        "123456",
        "user@@domain.com",
        "user@domain..com"
    ]
    
    for invalid in invalid_inputs:
        match = re.match(email_pattern, invalid)
        if match:
            print(f"⚠️  {invalid} - INCORRECTLY MATCHED")
        else:
            print(f"✅ {invalid} - CORRECTLY REJECTED")
    
    print("\nTesting with extra text (which should NOT match):")
    mixed_inputs = [
        "My email is user@gmail.com please",
        "user@gmail.com is my email",
        "Contact me at user@gmail.com for more info",
        "Email: user@gmail.com"
    ]
    
    for mixed in mixed_inputs:
        match = re.match(email_pattern, mixed)
        if match:
            print(f"⚠️  '{mixed}' - MATCHED: '{match.group()}'")
        else:
            print(f"✅ '{mixed}' - CORRECTLY REJECTED (contains extra text)")
    
    print("\n" + "=" * 40)
    print("DIAGNOSIS:")
    print("The regex uses re.match() which only matches from the START of the string.")
    print("If users send extra text like 'my email is user@gmail.com', it won't match.")
    print("We should either:")
    print("1. Use re.search() to find email anywhere in the text")
    print("2. Or improve email extraction logic")

if __name__ == '__main__':
    test_email_regex()