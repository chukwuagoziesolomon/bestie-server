#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bestyy.config.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from bestyy.core_features.user.services.paystack_service import PaystackService

def check_opay_bank():
    service = PaystackService()
    result = service.get_supported_banks()

    if result['success']:
        opay_banks = [bank for bank in result['banks'] if 'opay' in bank.get('name', '').lower() or 'opay' in bank.get('slug', '').lower()]
        print('OPay banks found:')
        for bank in opay_banks:
            print(f'  Name: {bank.get("name")}, Code: {bank.get("code")}, Slug: {bank.get("slug")}')

        if not opay_banks:
            print('No OPay banks found in supported banks list')
            print('First 5 banks:')
            for bank in result['banks'][:5]:
                print(f'  Name: {bank.get("name")}, Code: {bank.get("code")}')
    else:
        print(f'Error getting banks: {result}')

if __name__ == '__main__':
    check_opay_bank()