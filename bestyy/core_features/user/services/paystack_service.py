import requests
from django.conf import settings
from django.utils import timezone
from bestyy.core_features.user.models import User
import logging

logger = logging.getLogger(__name__)


class PaystackService:
    """
    Service for interacting with Paystack API

    Note: Split payment logic (subaccount splits at checkout) is now deprecated/removed. All payouts to vendors/couriers
    are done using Paystack single or bulk transfer after OTP confirmation (see trigger_vendor_payout and trigger_courier_payout).
    """

    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = settings.PAYSTACK_BASE_URL
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, method, endpoint, data=None):
        """Make HTTP request to Paystack API"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, params=data)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=self.headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API error: {str(e)}")
            return None

    def create_customer(self, user):
        """Create a customer on Paystack"""
        data = {
            'email': user.email,
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'phone': getattr(user.profile, 'phone', '') if hasattr(user, 'profile') else ''
        }

        response = self._make_request('POST', '/customer', data)

        if response and response.get('status'):
            customer_data = response.get('data', {})
            return {
                'customer_id': customer_data.get('customer_code'),
                'success': True
            }

        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    def create_dedicated_account(self, user, preferred_bank='titan-paystack'):
        """Create a dedicated virtual account for a user"""

        # First, ensure customer exists
        customer_result = self.create_customer(user)
        if not customer_result['success']:
            return customer_result

        customer_id = customer_result['customer_id']

        # Create dedicated account
        data = {
            'customer': customer_id,
            'preferred_bank': preferred_bank
        }

        response = self._make_request('POST', '/dedicated_account', data)

        if response and response.get('status'):
            account_data = response.get('data', {})

            # Save to database
            dva, created = DedicatedVirtualAccount.objects.update_or_create(
                user=user,
                defaults={
                    'paystack_customer_id': customer_id,
                    'paystack_dedicated_account_id': account_data.get('id'),
                    'bank_name': account_data.get('bank', {}).get('name', ''),
                    'bank_slug': account_data.get('bank', {}).get('slug', ''),
                    'account_number': account_data.get('account_number', ''),
                    'account_name': account_data.get('account_name', ''),
                    'is_active': account_data.get('active', True),
                    'is_assigned': account_data.get('assigned', True),
                    'assignment_type': account_data.get('assignment', {}).get('account_type')
                }
            )

            return {
                'success': True,
                'account': dva,
                'account_data': account_data
            }

        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    def assign_dedicated_account(self, user, preferred_bank='titan-paystack'):
        """Single-step account assignment (alternative to create_dedicated_account)"""

        data = {
            'email': user.email,
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'phone': getattr(user.profile, 'phone', '') if hasattr(user, 'profile') else '',
            'preferred_bank': preferred_bank,
            'country': 'NG'  # Nigeria
        }

        response = self._make_request('POST', '/dedicated_account/assign', data)

        if response and response.get('status'):
            account_data = response.get('data', {})

            # Save to database
            dva, created = DedicatedVirtualAccount.objects.update_or_create(
                user=user,
                defaults={
                    'paystack_customer_id': account_data.get('customer', {}).get('customer_code'),
                    'paystack_dedicated_account_id': account_data.get('id'),
                    'bank_name': account_data.get('bank', {}).get('name', ''),
                    'bank_slug': account_data.get('bank', {}).get('slug', ''),
                    'account_number': account_data.get('account_number', ''),
                    'account_name': account_data.get('account_name', ''),
                    'is_active': account_data.get('active', True),
                    'is_assigned': account_data.get('assigned', True),
                    'assignment_type': account_data.get('assignment', {}).get('account_type')
                }
            )

            return {
                'success': True,
                'account': dva,
                'account_data': account_data
            }

        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    def get_customer_accounts(self, user):
        """Get customer's dedicated accounts"""
        try:
            dva = DedicatedVirtualAccount.objects.get(user=user)
            customer_id = dva.paystack_customer_id

            response = self._make_request('GET', f'/customer/{customer_id}')

            if response and response.get('status'):
                return response.get('data', {}).get('dedicated_account', {})
            return None

        except DedicatedVirtualAccount.DoesNotExist:
            return None

    def requery_account(self, account_number, provider_slug='titan-paystack', date=None):
        """Requery dedicated account for pending transactions"""
        if date is None:
            date = timezone.now().date().isoformat()

        params = {
            'account_number': account_number,
            'provider_slug': provider_slug,
            'date': date
        }

        response = self._make_request('GET', '/dedicated_account/requery', params)

        if response and response.get('status'):
            return response.get('data', [])
        return []

    def bulk_transfer(self, transfer_items, currency='NGN', source='balance'):
        """
        Initiate bulk transfer (e.g. for vendor/courier payouts as a batch)
        transfer_items: list of dicts - each dict contains amount, reference, reason, recipient
        """
        data = {
            'currency': currency,
            'source': source,
            'transfers': transfer_items
        }
        response = self._make_request('POST', '/transfer/bulk', data)
        if response and response.get('status'):
            return {'success': True, 'data': response.get('data', [])}
        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    # Deprecated split-related methods (for clarity)
    def create_subaccount(self, *args, **kwargs):
        """Deprecated: Do not use split payments; use transfer_recipient logic and payouts instead."""
        raise NotImplementedError('Subaccount/split logic is deprecated; use paystack recipients and direct transfers.')
    def add_split_payment(self, *args, **kwargs):
        """Deprecated: Do not use split payments."""
        raise NotImplementedError('Split logic is deprecated.')
    def remove_split_payment(self, *args, **kwargs):
        """Deprecated: Do not use split payments."""
        raise NotImplementedError('Split logic is deprecated.')

    def get_supported_banks(self):
        """Get list of supported banks for dedicated accounts"""
        response = self._make_request('GET', '/dedicated_account/available_providers')

        if response and response.get('status'):
            return response.get('data', [])
        return []

    def create_transfer_recipient(self, recipient_type, name, account_number, bank_code, currency='NGN'):
        """Create a transfer recipient for payouts"""

        data = {
            'type': recipient_type,  # 'nuban' for Nigerian bank accounts
            'name': name,
            'account_number': account_number,
            'bank_code': bank_code,
            'currency': currency
        }

        response = self._make_request('POST', '/transferrecipient', data)

        if response and response.get('status'):
            recipient_data = response.get('data', {})
            return {
                'recipient_code': recipient_data.get('recipient_code'),
                'success': True
            }

        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    def initiate_transfer(self, amount, recipient_code, reference, reason):
        """Initiate a transfer to a recipient"""

        data = {
            'source': 'balance',
            'amount': int(amount * 100),  # Convert to kobo
            'recipient': recipient_code,
            'reference': reference,
            'reason': reason
        }

        response = self._make_request('POST', '/transfer', data)

        if response and response.get('status'):
            transfer_data = response.get('data', {})
            return {
                'transfer_code': transfer_data.get('transfer_code'),
                'status': transfer_data.get('status'),
                'success': True
            }

        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    def verify_transfer(self, reference):
        """Verify transfer status"""

        response = self._make_request('GET', f'/transfer/verify/{reference}')

        if response and response.get('status'):
            return response.get('data', {})
        return None

    def initialize_transaction(self, payment_data):
        """Initialize a Paystack transaction with optional split payment"""

        # Extract required fields
        email = payment_data.get('email')
        amount = payment_data.get('amount')  # Amount in kobo
        reference = payment_data.get('reference')
        callback_url = payment_data.get('callback_url')
        metadata = payment_data.get('metadata', {})

        data = {
            'email': email,
            'amount': amount,
            'reference': reference,
            'callback_url': callback_url,
            'metadata': metadata
        }

        # Add split payment parameters if provided
        if 'subaccount' in payment_data:
            data['subaccount'] = payment_data['subaccount']
        if 'transaction_charge' in payment_data:
            data['transaction_charge'] = payment_data['transaction_charge']
        if 'bearer' in payment_data:
            data['bearer'] = payment_data['bearer']

        response = self._make_request('POST', '/transaction/initialize', data)

        if response and response.get('status'):
            return {
                'success': True,
                'authorization_url': response.get('data', {}).get('authorization_url'),
                'access_code': response.get('data', {}).get('access_code'),
                'reference': response.get('data', {}).get('reference')
            }

        return {
            'success': False,
            'error': response.get('message') if response else 'API Error'
        }

    def verify_bank_account(self, account_number, bank_code):
        """
        Verify bank account details using Paystack's resolve account endpoint
        """
        params = {
            'account_number': account_number,
            'bank_code': bank_code
        }

        response = self._make_request('GET', '/bank/resolve', params)

        if response and response.get('status'):
            account_data = response.get('data', {})
            return {
                'success': True,
                'account_number': account_data.get('account_number'),
                'account_name': account_data.get('account_name'),
                'bank_id': account_data.get('bank_id')
            }

        return {
            'success': False,
            'message': response.get('message') if response else 'Unable to verify bank account'
        }

    def get_supported_banks(self, country='nigeria'):
        """
        Get list of supported banks from Paystack API
        """
        params = {'country': country}

        response = self._make_request('GET', '/bank', params)

        if response and response.get('status'):
            return {
                'success': True,
                'banks': response.get('data', [])
            }

        return {
            'success': False,
            'banks': [],
            'error': response.get('message') if response else 'Unable to fetch banks'
        }