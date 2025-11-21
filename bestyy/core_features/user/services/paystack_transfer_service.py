"""
Paystack Transfer Service for automated payments to vendors and couriers.
Handles transfer recipient creation, transfer initiation, and status verification.
"""
import requests
import logging
from django.conf import settings
from decimal import Decimal
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class PaystackTransferService:
    """Service for handling Paystack transfers to vendors and couriers."""
    
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def create_transfer_recipient(
        self,
        account_number: str,
        bank_code: str,
        name: str,
        recipient_type: str = 'nuban',
        currency: str = 'NGN',
        metadata: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a transfer recipient on Paystack.
        
        Args:
            account_number: Bank account number
            bank_code: Bank code (e.g., '044' for Access Bank)
            name: Account holder name
            recipient_type: Type of recipient (nuban, mobile_money, etc.)
            currency: Currency code (NGN, GHS, KES, ZAR)
            metadata: Additional metadata to store
        
        Returns:
            Dict with recipient_code and other details, or None if failed
        """
        url = f"{self.BASE_URL}/transferrecipient"
        
        payload = {
            'type': recipient_type,
            'name': name,
            'account_number': account_number,
            'bank_code': bank_code,
            'currency': currency
        }
        
        if metadata:
            payload['metadata'] = metadata
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status'):
                recipient_data = data.get('data', {})
                logger.info(f"✅ Transfer recipient created: {recipient_data.get('recipient_code')}")
                return recipient_data
            else:
                logger.error(f"❌ Failed to create recipient: {data.get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error creating transfer recipient: {str(e)}")
            return None
    
    def initiate_transfer(
        self,
        amount: Decimal,
        recipient_code: str,
        reference: str,
        reason: str,
        source: str = 'balance'
    ) -> Optional[Dict[str, Any]]:
        """
        Initiate a transfer to a recipient.
        
        Args:
            amount: Amount to transfer in kobo (e.g., 10000 = ₦100.00)
            recipient_code: Recipient code from create_transfer_recipient
            reference: Unique transfer reference (16-50 chars, lowercase, digits, _ -)
            reason: Reason for transfer
            source: Source of funds ('balance' or other)
        
        Returns:
            Dict with transfer details, or None if failed
        """
        url = f"{self.BASE_URL}/transfer"
        
        # Convert amount to kobo (smallest unit)
        amount_in_kobo = int(amount * 100)
        
        payload = {
            'source': source,
            'amount': amount_in_kobo,
            'recipient': recipient_code,
            'reference': reference,
            'reason': reason
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status'):
                transfer_data = data.get('data', {})
                logger.info(f"✅ Transfer initiated: {transfer_data.get('transfer_code')} - Status: {transfer_data.get('status')}")
                return transfer_data
            else:
                logger.error(f"❌ Failed to initiate transfer: {data.get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error initiating transfer: {str(e)}")
            return None
    
    def verify_transfer(self, reference: str) -> Optional[Dict[str, Any]]:
        """
        Verify the status of a transfer using its reference.
        
        Args:
            reference: Transfer reference used during initiation
        
        Returns:
            Dict with transfer status and details, or None if failed
        """
        url = f"{self.BASE_URL}/transfer/verify/{reference}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status'):
                transfer_data = data.get('data', {})
                logger.info(f"✅ Transfer verified: {reference} - Status: {transfer_data.get('status')}")
                return transfer_data
            else:
                logger.error(f"❌ Failed to verify transfer: {data.get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error verifying transfer: {str(e)}")
            return None
    
    def get_banks(self, country: str = 'nigeria', currency: str = 'NGN') -> Optional[list]:
        """
        Get list of supported banks for a country.
        
        Args:
            country: Country name (e.g., 'nigeria', 'ghana', 'kenya', 'south africa')
            currency: Currency code (NGN, GHS, KES, ZAR)
        
        Returns:
            List of banks with name and code, or None if failed
        """
        url = f"{self.BASE_URL}/bank"
        params = {
            'country': country,
            'currency': currency
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status'):
                banks = data.get('data', [])
                logger.info(f"✅ Retrieved {len(banks)} banks for {country}")
                return banks
            else:
                logger.error(f"❌ Failed to get banks: {data.get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error getting banks: {str(e)}")
            return None
    
    def retry_transfer(
        self,
        reference: str,
        recipient_code: str,
        amount: Decimal,
        reason: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retry a failed transfer with the same reference to prevent double crediting.
        
        Args:
            reference: Same reference used in the original transfer
            recipient_code: Recipient code
            amount: Amount to transfer
            reason: Reason for transfer
        
        Returns:
            Dict with transfer details, or None if failed
        """
        logger.info(f"🔄 Retrying transfer with reference: {reference}")
        return self.initiate_transfer(
            amount=amount,
            recipient_code=recipient_code,
            reference=reference,
            reason=reason
        )


class OrderPaymentAutomation:
    """Handles automatic payments to vendors and couriers when codes are verified."""
    
    def __init__(self):
        self.transfer_service = PaystackTransferService()
    
    def pay_vendor_on_pickup(self, order) -> bool:
        """
        Automatically transfer payment to vendor when pickup code is verified.
        
        Args:
            order: Order instance with verified pickup code
        
        Returns:
            True if payment initiated successfully, False otherwise
        """
        from django.utils import timezone
        
        # Check if already paid
        if order.vendor_paid:
            logger.warning(f"⚠️ Vendor already paid for order {order.order_number}")
            return False
        
        # Check if vendor has recipient code
        if not hasattr(order.vendor, 'paystack_recipient_code') or not order.vendor.paystack_recipient_code:
            logger.error(f"❌ Vendor {order.vendor.id} has no Paystack recipient code")
            return False
        
        # Calculate vendor payout
        payouts = order.calculate_payouts()
        vendor_amount = payouts['vendor_amount']
        
        # Initiate transfer
        transfer_result = self.transfer_service.initiate_transfer(
            amount=vendor_amount,
            recipient_code=order.vendor.paystack_recipient_code,
            reference=order.vendor_transfer_reference,
            reason=f"Payment for order {order.order_number} - Pickup confirmed"
        )
        
        if transfer_result:
            # Update order with transfer details
            order.vendor_transfer_code = transfer_result.get('transfer_code')
            order.vendor_transfer_status = transfer_result.get('status', 'processing')
            
            # Mark as paid if transfer is successful or pending
            if transfer_result.get('status') in ['success', 'pending']:
                order.vendor_paid = True
                order.vendor_paid_at = timezone.now()
            
            order.save()
            
            logger.info(f"✅ Vendor payment initiated for order {order.order_number}: ₦{vendor_amount}")
            return True
        else:
            logger.error(f"❌ Failed to initiate vendor payment for order {order.order_number}")
            return False
    
    def pay_courier_on_delivery(self, order) -> bool:
        """
        Automatically transfer payment to courier when delivery OTP is verified.
        
        Args:
            order: Order instance with verified delivery OTP
        
        Returns:
            True if payment initiated successfully, False otherwise
        """
        from django.utils import timezone
        
        # Check if already paid
        if order.courier_paid:
            logger.warning(f"⚠️ Courier already paid for order {order.order_number}")
            return False
        
        # Check if courier exists
        if not order.courier:
            logger.error(f"❌ No courier assigned to order {order.order_number}")
            return False
        
        # Check if courier has recipient code
        if not hasattr(order.courier, 'paystack_recipient_code') or not order.courier.paystack_recipient_code:
            logger.error(f"❌ Courier {order.courier.id} has no Paystack recipient code")
            return False
        
        # Calculate courier payout
        payouts = order.calculate_payouts()
        courier_amount = payouts['courier_amount']
        
        # Initiate transfer
        transfer_result = self.transfer_service.initiate_transfer(
            amount=courier_amount,
            recipient_code=order.courier.paystack_recipient_code,
            reference=order.courier_transfer_reference,
            reason=f"Payment for order {order.order_number} - Delivery confirmed"
        )
        
        if transfer_result:
            # Update order with transfer details
            order.courier_transfer_code = transfer_result.get('transfer_code')
            order.courier_transfer_status = transfer_result.get('status', 'processing')
            
            # Mark as paid if transfer is successful or pending
            if transfer_result.get('status') in ['success', 'pending']:
                order.courier_paid = True
                order.courier_paid_at = timezone.now()
            
            order.save()
            
            logger.info(f"✅ Courier payment initiated for order {order.order_number}: ₦{courier_amount}")
            return True
        else:
            logger.error(f"❌ Failed to initiate courier payment for order {order.order_number}")
            return False
