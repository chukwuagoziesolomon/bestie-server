"""
Cryptocurrency payment services for NOWPayments integration
"""
import requests
import json
import time
import logging
import hashlib
import hmac
from decimal import Decimal
from typing import Dict, Optional, Tuple
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from bestyy.restaurant_features.order.models import Order
# CryptoPayment model removed - crypto payments not implemented

logger = logging.getLogger(__name__)


class CryptoRateService:
    """Service for handling cryptocurrency exchange rates and conversions"""

    def __init__(self):
        self.nowpayments_api = "https://api.nowpayments.io/v1"
        self.api_key = getattr(settings, 'NOWPAYMENTS_API_KEY', '')
        self.cache_timeout = 60  # Cache rates for 60 seconds

    def get_exchange_rate(self, from_currency: str = "ngn", to_currency: str = "btc") -> Optional[Decimal]:
        """Get real-time exchange rate from Naira to crypto"""

        # Check cache first
        cache_key = f"crypto_rate_{from_currency}_{to_currency}"
        cached_rate = cache.get(cache_key)
        if cached_rate:
            return Decimal(str(cached_rate))

        if not self.api_key:
            logger.warning("NOWPayments API key not configured")
            return None

        try:
            response = requests.get(
                f"{self.nowpayments_api}/estimate",
                headers={"x-api-key": self.api_key},
                params={
                    "amount": 1000,  # Base amount for rate calculation
                    "currency_from": from_currency,
                    "currency_to": to_currency
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                rate = Decimal(str(data["estimated_amount"])) / Decimal('1000')

                # Cache the rate
                cache.set(cache_key, float(rate), self.cache_timeout)
                logger.info(f"Cached exchange rate: 1000 {from_currency} = {rate} {to_currency}")
                return rate

            else:
                logger.error(f"Failed to fetch exchange rate: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error fetching exchange rate: {str(e)}")
            return None

    def calculate_crypto_amount(self, naira_amount: Decimal, crypto_currency: str) -> Dict:
        """Calculate crypto amount for given Naira amount"""

        exchange_rate = self.get_exchange_rate("ngn", crypto_currency)
        if not exchange_rate:
            raise Exception("Unable to fetch exchange rate")

        crypto_amount = naira_amount * exchange_rate

        # Check minimum payment amount
        min_amount = self.get_minimum_payment(crypto_currency)
        if crypto_amount < min_amount:
            raise Exception(f"Amount too small. Minimum {crypto_currency.upper()} payment: {min_amount}")

        return {
            "crypto_amount": crypto_amount,
            "exchange_rate": exchange_rate,
            "original_naira": naira_amount,
            "crypto_currency": crypto_currency,
            "minimum_amount": min_amount
        }

    def get_minimum_payment(self, crypto_currency: str) -> Decimal:
        """Get minimum payment amount for specific crypto (with caching)"""
        cache_key = f"crypto_minimum_{crypto_currency}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Decimal(str(cached))

        if not self.api_key:
            # Return conservative minimums if API key not configured
            minimums = {
                'btc': Decimal('0.0001'),
                'eth': Decimal('0.001'),
                'usdt': Decimal('1'),
                'bnb': Decimal('0.01')
            }
            return minimums.get(crypto_currency.lower(), Decimal('0.0001'))

        try:
            response = requests.get(
                f"{self.nowpayments_api}/min-amount",
                headers={"x-api-key": self.api_key},
                params={
                    "currency_from": crypto_currency,
                    "currency_to": "ngn"
                },
                timeout=10
            )

            if response.status_code == 200:
                amt = Decimal(str(response.json()["min_amount"]))
                cache.set(cache_key, float(amt), self.minimum_cache_timeout)
                return amt

        except Exception as e:
            logger.error(f"Error fetching minimum amount: {str(e)}")

        # Fallback minimums
        fallback_minimums = {
            'btc': Decimal('0.0001'),
            'eth': Decimal('0.001'),
            'usdt': Decimal('1'),
            'bnb': Decimal('0.01')
        }
        return fallback_minimums.get(crypto_currency.lower(), Decimal('0.0001'))


class NOWPaymentsService:
    """Service for interacting with NOWPayments API"""

    def __init__(self):
        self.api_url = "https://api.nowpayments.io/v1"
        self.api_key = getattr(settings, 'NOWPAYMENTS_API_KEY', '')

    def create_payment(self, naira_amount: Decimal, crypto_currency: str, order_id: str,
                      callback_url: str = None) -> Dict:
        """Create a new crypto payment"""

        if not self.api_key:
            raise Exception("NOWPayments API key not configured")

        # Calculate crypto amount
        rate_service = CryptoRateService()
        crypto_data = rate_service.calculate_crypto_amount(naira_amount, crypto_currency)

        # Prepare payment data
        payment_data = {
            "price_amount": float(naira_amount),
            "price_currency": "ngn",
            "pay_currency": crypto_currency,
            "order_id": order_id,
            "order_description": f"Food delivery order #{order_id}",
            "is_fixed_rate": False,  # Use floating rate for now
            "is_fee_paid_by_user": False
        }

        if callback_url:
            payment_data["ipn_callback_url"] = callback_url

        try:
            response = requests.post(
                f"{self.api_url}/payment",
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                data=json.dumps(payment_data),
                timeout=15
            )

            if response.status_code == 201:
                payment_response = response.json()

                return {
                    "success": True,
                    "payment_id": payment_response["payment_id"],
                    "pay_address": payment_response["pay_address"],
                    "pay_amount": payment_response["pay_amount"],
                    "pay_currency": payment_response["pay_currency"],
                    "payment_status": payment_response["payment_status"],
                    "crypto_data": crypto_data
                }
            else:
                logger.error(f"Failed to create payment: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_payment_status(self, payment_id: str) -> Dict:
        """Get payment status from NOWPayments"""

        if not self.api_key:
            return {"success": False, "error": "API key not configured"}

        try:
            response = requests.get(
                f"{self.api_url}/payment/{payment_id}",
                headers={"x-api-key": self.api_key},
                timeout=10
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "payment_data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Error fetching payment status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_available_currencies(self) -> Dict:
        """Get list of available cryptocurrencies"""

        if not self.api_key:
            return {"success": False, "error": "API key not configured"}

        try:
            response = requests.get(
                f"{self.api_url}/currencies",
                headers={"x-api-key": self.api_key},
                timeout=10
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "currencies": response.json()["currencies"]
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Error fetching currencies: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


class CryptoPaymentManager:
    """Manager for handling crypto payment operations"""

    def __init__(self):
        self.nowpayments = NOWPaymentsService()
        self.rate_service = CryptoRateService()
        self.minimum_cache_timeout = 1800  # 30 min for min amount cache

    def create_crypto_payment(self, order: Order, crypto_currency: str = "btc"):
        """Create a crypto payment for an order - NOT IMPLEMENTED"""
        raise NotImplementedError("Crypto payments are not implemented in this version")

    def process_webhook(self, webhook_data: Dict, signature: str = None) -> bool:
        """Process webhook from NOWPayments - NOT IMPLEMENTED"""
        raise NotImplementedError("Crypto payments are not implemented in this version")

    def verify_webhook_signature(self, webhook_data: Dict, signature: str) -> bool:
        """Verify webhook signature using HMAC"""

        ipn_secret = getattr(settings, 'NOWPAYMENTS_IPN_SECRET', '')
        if not ipn_secret:
            logger.warning("IPN secret not configured")
            return True  # Skip verification in development

        try:
            # Sort webhook data
            sorted_data = json.dumps(webhook_data, separators=(',', ':'), sort_keys=True)
            calculated_signature = hmac.new(
                ipn_secret.encode(),
                sorted_data.encode(),
                hashlib.sha512
            ).hexdigest()

            return hmac.compare_digest(calculated_signature, signature)

        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False

    def handle_successful_payment(self, crypto_payment):
        """Handle successful payment completion - NOT IMPLEMENTED"""
        raise NotImplementedError("Crypto payments are not implemented in this version")

    def get_supported_cryptocurrencies(self) -> Dict:
        """Get list of supported cryptocurrencies with current rates"""

        try:
            currencies_response = self.nowpayments.get_available_currencies()
            if not currencies_response["success"]:
                return currencies_response

            supported_cryptos = []
            rate_service = CryptoRateService()

            for currency in currencies_response["currencies"][:10]:  # Top 10 currencies
                rate = rate_service.get_exchange_rate("ngn", currency)
                min_amount = rate_service.get_minimum_payment(currency)

                if rate:
                    supported_cryptos.append({
                        "code": currency,
                        "name": currency.upper(),
                        "rate": float(rate),
                        "minimum": float(min_amount)
                    })

            return {
                "success": True,
                "cryptocurrencies": supported_cryptos
            }

        except Exception as e:
            logger.error(f"Error getting supported cryptocurrencies: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _format_payment_data(self, crypto_payment):
        """Format payment data - NOT IMPLEMENTED"""
        raise NotImplementedError("Crypto payments are not implemented in this version")