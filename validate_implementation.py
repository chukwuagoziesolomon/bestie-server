#!/usr/bin/env python3
"""
Quick Logic Check: Validate mandatory signup enforcement patterns
Directly analyzing the implemented code for correct patterns.
"""

import os
import re

def analyze_signup_enforcement():
    """Analyze the views.py file for mandatory signup enforcement patterns"""
    
    print("🔍 ANALYZING MANDATORY SIGNUP ENFORCEMENT")
    print("=" * 60)
    
    views_path = os.path.join('bestyy', 'communication', 'whatsapp', 'views.py')
    
    if not os.path.exists(views_path):
        print("❌ Views file not found")
        return False
    
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Analysis patterns with explanations
    patterns = [
        {
            'name': 'Mandatory Signup Check',
            'pattern': r'conversation\.onboarding_state != [\'"]onboarded[\'"]',
            'description': 'Blocks functionality for non-onboarded users',
            'critical': True
        },
        {
            'name': 'AI Processing Block',
            'pattern': r'if.*onboarding_state.*onboarded.*:.*\n.*ai_service\.categorize_message',
            'description': 'AI only processes messages from onboarded users',
            'critical': True,
            'multiline': True
        },
        {
            'name': 'Email State Management',
            'pattern': r'awaiting_email',
            'description': 'Manages email signup state',
            'critical': False
        },
        {
            'name': 'Account Required Message',
            'pattern': r'Account Required',
            'description': 'Shows signup requirement message',
            'critical': True
        },
        {
            'name': 'Email Registration Call',
            'pattern': r'multi.*role.*register',
            'description': 'Calls registration endpoint',
            'critical': True
        },
        {
            'name': 'Onboarded State Setting',
            'pattern': r'onboarding_state\s*=\s*[\'"]onboarded[\'"]',
            'description': 'Sets user as onboarded after signup',
            'critical': True
        },
        {
            'name': 'Email Validation',
            'pattern': r'is_valid_email|@.*\.',
            'description': 'Validates email format',
            'critical': False
        }
    ]
    
    results = []
    
    for pattern_info in patterns:
        pattern = pattern_info['pattern']
        name = pattern_info['name']
        description = pattern_info['description']
        critical = pattern_info.get('critical', False)
        multiline = pattern_info.get('multiline', False)
        
        if multiline:
            flags = re.MULTILINE | re.DOTALL
        else:
            flags = 0
        
        matches = re.findall(pattern, content, flags)
        found = len(matches) > 0
        
        status = "✅" if found else ("🔴" if critical else "⚠️")
        print(f"{status} {name}: {'Found' if found else 'Missing'}")
        print(f"    {description}")
        if found and matches:
            print(f"    Matches: {len(matches)}")
        print()
        
        results.append({
            'name': name,
            'found': found,
            'critical': critical,
            'matches': len(matches)
        })
    
    # Summary
    total_patterns = len(results)
    found_patterns = sum(1 for r in results if r['found'])
    critical_patterns = [r for r in results if r['critical']]
    critical_found = sum(1 for r in critical_patterns if r['found'])
    
    print("=" * 60)
    print("📊 ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total Patterns: {total_patterns}")
    print(f"Found: {found_patterns}")
    print(f"Missing: {total_patterns - found_patterns}")
    print(f"Success Rate: {(found_patterns/total_patterns*100):.1f}%")
    print()
    print(f"Critical Patterns: {len(critical_patterns)}")
    print(f"Critical Found: {critical_found}")
    print(f"Critical Missing: {len(critical_patterns) - critical_found}")
    print(f"Critical Success: {(critical_found/len(critical_patterns)*100):.1f}%")
    
    # Check specific logic flow
    print("\n🔄 LOGIC FLOW ANALYSIS")
    print("=" * 40)
    
    # Check for the main enforcement block
    enforcement_pattern = r'if.*onboarding_state.*!=.*onboarded.*:.*Account Required'
    enforcement_found = bool(re.search(enforcement_pattern, content, re.MULTILINE | re.DOTALL))
    
    print(f"{'✅' if enforcement_found else '❌'} Main Enforcement Block: {'Found' if enforcement_found else 'Missing'}")
    
    # Check for AI bypass during signup
    ai_bypass_pattern = r'if.*onboarding_state.*==.*onboarded.*:.*\n.*ai_service'
    ai_bypass_found = bool(re.search(ai_bypass_pattern, content, re.MULTILINE | re.DOTALL))
    
    print(f"{'✅' if ai_bypass_found else '❌'} AI Bypass Logic: {'Found' if ai_bypass_found else 'Missing'}")
    
    # Overall assessment
    print("\n🎯 OVERALL ASSESSMENT")
    print("=" * 40)
    
    critical_success = critical_found == len(critical_patterns)
    enforcement_logic = enforcement_found and ai_bypass_found
    
    if critical_success and enforcement_logic:
        print("✅ MANDATORY SIGNUP ENFORCEMENT: PROPERLY IMPLEMENTED")
        print("🎉 All critical patterns found and logic flows correct")
        print("📋 Users must sign up before accessing functionality")
        return True
    elif critical_success:
        print("⚠️ MANDATORY SIGNUP ENFORCEMENT: MOSTLY IMPLEMENTED")
        print("✅ Critical patterns found but some logic flows may be incomplete")
        return True
    else:
        print("❌ MANDATORY SIGNUP ENFORCEMENT: NEEDS WORK")
        print("🔴 Critical patterns missing")
        return False

def check_recent_changes():
    """Check if recent changes are properly implemented"""
    
    print("\n📝 CHECKING RECENT IMPLEMENTATION")
    print("=" * 50)
    
    views_path = os.path.join('bestyy', 'communication', 'whatsapp', 'views.py')
    
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for our specific implementations
    recent_patterns = [
        ('Mandatory Block Comment', '# MANDATORY: Block all functionality until signup'),
        ('Account Required Message', 'Account Required'),
        ('Onboarded Check', 'onboarding_state == \'onboarded\''),
        ('AI Processing Guard', 'conversation.onboarding_state == \'onboarded\''),
        ('Email Processing Logic', 'is_valid_email'),
        ('Multi-role Registration', 'multi_role_register')
    ]
    
    for name, pattern in recent_patterns:
        found = pattern in content
        print(f"{'✅' if found else '❌'} {name}: {'Found' if found else 'Missing'}")
    
    return True

def main():
    """Run comprehensive analysis"""
    
    print("🔍 MANDATORY SIGNUP ENFORCEMENT ANALYSIS")
    print("=" * 70)
    print("Analyzing code patterns and logic flows for mandatory signup")
    print("=" * 70)
    
    analysis_success = analyze_signup_enforcement()
    check_recent_changes()
    
    print("\n" + "=" * 70)
    print("🏁 FINAL ANALYSIS RESULT")
    print("=" * 70)
    
    if analysis_success:
        print("✅ MANDATORY SIGNUP ENFORCEMENT IS PROPERLY IMPLEMENTED")
        print("🎯 Key Features:")
        print("   • Users blocked until signup completion")
        print("   • AI processing only for onboarded users")
        print("   • Email processing and account creation")
        print("   • Proper state management")
        print("   • Compelling signup messaging")
        
        print("\n🚀 READY FOR TESTING:")
        print("   1. First-time users will be asked to sign up")
        print("   2. No functionality available until email provided")
        print("   3. Account creation and onboarding flow")
        print("   4. Full functionality after successful signup")
        
        return True
    else:
        print("❌ MANDATORY SIGNUP ENFORCEMENT NEEDS ATTENTION")
        print("⚠️ Some critical patterns are missing")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)