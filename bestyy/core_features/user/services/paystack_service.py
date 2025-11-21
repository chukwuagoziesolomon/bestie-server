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

        except requests.exceptions.HTTPError as e:
            # For HTTP errors (4xx, 5xx), try to extract error message from response
            try:
                error_data = response.json()
                error_message = error_data.get('message', str(e))
                logger.error(f"Paystack API HTTP error: {error_message}")
                return {'status': False, 'message': error_message}
            except (ValueError, AttributeError):
                logger.error(f"Paystack API HTTP error: {str(e)}")
                return {'status': False, 'message': str(e)}
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API request error: {str(e)}")
            return {'status': False, 'message': str(e)}

    def create_customer(self, user, phone_number=None):
        """Create a customer on Paystack"""
        # Use provided phone number, or fall back to user profile
        phone = phone_number or (getattr(user.profile, 'phone', '') if hasattr(user, 'profile') else '')

        data = {
            'email': user.email,
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'phone': phone
        }

        response = self._make_request('POST', '/customer', data)

        if response and response.get('status'):
            customer_data = response.get('data', {})
            return {
                'customer_id': customer_data.get('customer_code'),
                'success': True
            }

        return {'success': False, 'error': response.get('message') if response else 'API Error'}






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

    def initialize_pay_with_transfer(self, email, amount, reference=None, expiry_hours=8):
        """
        Initialize Pay with Transfer - creates temporary bank account for single transaction

        Args:
            email (str): Customer email
            amount (int): Amount in kobo (smallest currency unit)
            reference (str, optional): Unique reference
            expiry_hours (int): Hours until account expires (1-8)

        Returns:
            dict: {'success': bool, 'account_details': dict or 'error': str}
        """
        import uuid
        from datetime import datetime, timedelta

        if not reference:
            reference = f"pwt_{uuid.uuid4().hex[:12]}"

        # Calculate expiry time - default to 8 hours if invalid
        if not (1 <= expiry_hours <= 8):
            expiry_hours = 8

        expires_at = (datetime.utcnow() + timedelta(hours=expiry_hours)).isoformat() + 'Z'

        data = {
            'email': email,
            'amount': amount,
            'reference': reference,
            'bank_transfer': {
                'account_expires_at': expires_at
            }
        }

        logger.info(f"Initializing Pay with Transfer for {email}, amount: ₦{amount/100:.2f}")

        response = self._make_request('POST', '/charge', data)

        if response and response.get('status'):
            charge_data = response.get('data', {})

            # Extract banking details - for Pay with Transfer, account details are in charge_data
            account_number = charge_data.get('account_number')
            account_name = charge_data.get('account_name')

            # Handle bank info - can be string or dict
            bank_info = charge_data.get('bank', {})
            if isinstance(bank_info, dict):
                bank_name = bank_info.get('name', 'Paystack Bank Transfer')
            else:
                bank_name = bank_info or 'Paystack Bank Transfer'

            customer_info = charge_data.get('customer', {})

            # Use account_expires_at from API response if available
            actual_expires_at = charge_data.get('account_expires_at', expires_at)

            account_details = {
                'account_number': account_number,
                'account_name': account_name,
                'bank_name': bank_name,
                'amount_expected': charge_data.get('amount', 0) / 100,  # Convert back to naira
                'reference': reference,
                'expires_at': actual_expires_at,
                'charge_id': charge_data.get('id'),
                'customer_email': customer_info.get('email'),
                'status': charge_data.get('status')
            }

            # Validate we got the essential banking details
            if not all([account_details['account_number'], account_details['account_name']]):
                logger.error("Pay with Transfer missing account details")
                return {'success': False, 'error': 'Bank account details not provided'}

            logger.info(f"Pay with Transfer initialized: Account {account_details['account_number']} expires {expires_at}")

            return {
                'success': True,
                'account_details': account_details,
                'charge_data': charge_data
            }
        else:
            error_msg = response.get('message') if response else 'API Error'
            logger.error(f"Pay with Transfer initialization failed: {error_msg}")
            return {'success': False, 'error': error_msg}

    def initialize_transaction(self, payment_data):
        """Initialize a Paystack transaction with optional split payment"""

        # Extract required fields
        email = payment_data.get('email')
        amount = payment_data.get('amount')  # Amount in kobo
        reference = payment_data.get('reference')
        callback_url = payment_data.get('callback_url')
        metadata = payment_data.get('metadata', {})

        # Validate required fields
        if not email:
            return {'success': False, 'error': 'Email is required'}
        if not amount or amount < 10000:  # Paystack minimum is ₦100 = 10,000 kobo
            return {'success': False, 'error': 'Amount must be at least ₦100 (10,000 kobo)'}
        if not reference:
            return {'success': False, 'error': 'Reference is required'}

        # Validate email format
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return {'success': False, 'error': 'Invalid email format'}

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

    # Subscription-related methods
    def create_plan(self, name, interval, amount, description=None, invoice_limit=None):
        """
        Create a subscription plan on Paystack

        Args:
            name (str): Plan name
            interval (str): 'hourly', 'daily', 'weekly', 'monthly', 'quarterly', 'biannually', 'annually'
            amount (int): Amount in kobo (smallest currency unit)
            description (str, optional): Plan description
            invoice_limit (int, optional): Maximum number of charges

        Returns:
            dict: {'success': bool, 'plan_code': str or 'error': str}
        """
        data = {
            'name': name,
            'interval': interval,
            'amount': amount
        }

        if description:
            data['description'] = description
        if invoice_limit:
            data['invoice_limit'] = invoice_limit

        response = self._make_request('POST', '/plan', data)

        if response and response.get('status'):
            plan_data = response.get('data', {})
            return {
                'success': True,
                'plan_code': plan_data.get('plan_code'),
                'plan_data': plan_data
            }

        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    def create_subscription(self, customer_code, plan_code, authorization_code=None, start_date=None):
        """
        Create a subscription for a customer

        Args:
            customer_code (str): Paystack customer code
            plan_code (str): Paystack plan code
            authorization_code (str, optional): Specific authorization to use
            start_date (str, optional): ISO 8601 date string for first charge

        Returns:
            dict: {'success': bool, 'subscription_code': str or 'error': str}
        """
        data = {
            'customer': customer_code,
            'plan': plan_code
        }

        if authorization_code:
            data['authorization'] = authorization_code
        if start_date:
            data['start_date'] = start_date

        response = self._make_request('POST', '/subscription', data)

        if response and response.get('status'):
            subscription_data = response.get('data', {})
            return {
                'success': True,
                'subscription_code': subscription_data.get('subscription_code'),
                'subscription_data': subscription_data
            }

        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    def initialize_subscription_transaction(self, email, plan_code, amount=None, interval=None):
        """
        Initialize a transaction that creates a subscription upon payment

        Args:
            email (str): Customer email
            plan_code (str): Paystack plan code
            amount (int, optional): Override plan amount in kobo
            interval (str, optional): Override plan interval ('daily', 'weekly', 'monthly')

        Returns:
            dict: {'success': bool, 'authorization_url': str or 'error': str}
        """
        data = {
            'email': email,
            'plan': plan_code
        }

        if amount:
            data['amount'] = amount

        # Note: Paystack doesn't support interval override in transaction initialization
        # The interval is set at the plan level

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

    def get_subscription(self, subscription_code):
        """
        Get subscription details

        Args:
            subscription_code (str): Paystack subscription code

        Returns:
            dict: Subscription data or None
        """
        response = self._make_request('GET', f'/subscription/{subscription_code}')

        if response and response.get('status'):
            return response.get('data', {})
        return None

    def list_subscriptions(self, customer=None, plan=None):
        """
        List subscriptions with optional filtering

        Args:
            customer (str, optional): Filter by customer code
            plan (str, optional): Filter by plan code

        Returns:
            list: List of subscriptions
        """
        params = {}
        if customer:
            params['customer'] = customer
        if plan:
            params['plan'] = plan

        response = self._make_request('GET', '/subscription', params)

        if response and response.get('status'):
            return response.get('data', [])
        return []

    def disable_subscription(self, subscription_code, token=None):
        """
        Disable/cancel a subscription

        Args:
            subscription_code (str): Paystack subscription code
            token (str, optional): Email token for confirmation

        Returns:
            dict: {'success': bool, 'error': str}
        """
        data = {}
        if token:
            data['token'] = token

        response = self._make_request('POST', f'/subscription/disable/{subscription_code}', data)

        if response and response.get('status'):
            return {'success': True}

        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    def enable_subscription(self, subscription_code):
        """
        Enable a subscription

        Args:
            subscription_code (str): Paystack subscription code

        Returns:
            dict: {'success': bool, 'error': str}
        """
        response = self._make_request('POST', f'/subscription/enable/{subscription_code}')

        if response and response.get('status'):
            return {'success': True}

        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    def get_subscription_link(self, subscription_code):
        """
        Get subscription management link

        Args:
            subscription_code (str): Paystack subscription code

        Returns:
            dict: {'success': bool, 'link': str or 'error': str}
        """
        response = self._make_request('GET', f'/subscription/{subscription_code}/manage/link')

        if response and response.get('status'):
            return {
                'success': True,
                'link': response.get('data', {}).get('link')
            }

        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    def send_subscription_update_email(self, subscription_code):
        """
        Send subscription management email

        Args:
            subscription_code (str): Paystack subscription code

        Returns:
            dict: {'success': bool, 'error': str}
        """
        response = self._make_request('POST', f'/subscription/{subscription_code}/manage/email')

        if response and response.get('status'):
            return {'success': True}

        return {'success': False, 'error': response.get('message') if response else 'API Error'}

    def verify_transaction(self, reference):
        """
        Verify transaction status using Paystack Verify API

        Args:
            reference (str): Transaction reference

        Returns:
            dict: {'success': bool, 'data': dict or 'error': str}
        """
        response = self._make_request('GET', f'/transaction/verify/{reference}')

        if response and response.get('status'):
            return {
                'success': True,
                'data': response.get('data', {})
            }

        return {
            'success': False,
            'error': response.get('message') if response else 'API Error'
        }
