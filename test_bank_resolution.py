#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from bestyy.core_features.user.services.paystack_service import PaystackService

def test_bank_resolution():
    paystack_service = PaystackService()
    banks_result = paystack_service.get_supported_banks()

    if banks_result['success']:
        bank_name = "OPay Digital Services Limited (OPay)"
        bank_name_lower = bank_name.lower().strip()

        print(f"Looking for bank: '{bank_name}'")
        print(f"Lower case: '{bank_name_lower}'")

        bank_code = None
        for bank in banks_result['banks']:
            bank_name_in_list = bank.get('name', '').lower().strip()
            bank_slug = bank.get('slug', '').lower()

            print(f"Checking bank: '{bank.get('name')}' (slug: {bank_slug})")

            if (bank_name_in_list == bank_name_lower or
                bank_name_lower in bank_name_in_list or
                bank_slug == bank_name_lower):
                bank_code = bank.get('code')
                print(f"FOUND MATCH! Bank code: {bank_code}")
                break

        if not bank_code:
            print("No match found with current logic")
            # Try partial word matching
            for bank in banks_result['banks']:
                if 'opay' in bank.get('name', '').lower():
                    bank_code = bank.get('code')
                    print(f"FOUND with 'opay' in name! Bank code: {bank_code}")
                    break

    else:
        print(f'Error getting banks: {banks_result}')

if __name__ == '__main__':
    test_bank_resolution()