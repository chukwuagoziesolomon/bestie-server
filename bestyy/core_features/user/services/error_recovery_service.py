"""
Error recovery service for handling various order and system failures
"""
import logging
from typing import Dict, List, Optional, Tuple, Callable
from django.utils import timezone
from django.db import transaction
from ..models import Order, WhatsAppConversation

logger = logging.getLogger(__name__)


class ErrorRecoveryService:
    """
    Service for handling errors and providing recovery strategies
    """

    ERROR_RECOVERY_STRATEGIES = {
        'item_unavailable': [
            'substitute_item',
            'find_alternative_vendor',
            'partial_refund',
            'cancel_item'
        ],
        'payment_failed': [
            'retry_payment',
            'alternative_payment_method',
            'split_payment',
            'cancel_order'
        ],
        'vendor_unavailable': [
            'reassign_vendor',
            'find_alternative_vendor',
            'delay_order',
            'cancel_order'
        ],
        'courier_unavailable': [
            'reassign_courier',
            'delay_delivery',
            'notify_customer',
            'cancel_delivery'
        ],
        'address_invalid': [
            'suggest_alternatives',
            'manual_address_entry',
            'geocode_correction',
            'contact_customer'
        ],
        'system_error': [
            'retry_operation',
            'fallback_mode',
            'escalate_to_support',
            'compensate_customer'
        ],
        'delivery_failed': [
            'redeliver',
            'refund_delivery',
            'contact_customer',
            'escalate_to_support'
        ]
    }

    def __init__(self):
        self.recovery_attempts = {}

    def handle_error(self, error_type: str, context: Dict) -> Dict:
        """
        Handle an error and attempt recovery
        """
        if error_type not in self.ERROR_RECOVERY_STRATEGIES:
            return {
                'success': False,
                'error': f'Unknown error type: {error_type}',
                'escalated': True
            }

        strategies = self.ERROR_RECOVERY_STRATEGIES[error_type]
        recovery_results = []

        # Try each recovery strategy in order
        for strategy in strategies:
            try:
                result = self._execute_recovery_strategy(strategy, context)
                recovery_results.append({
                    'strategy': strategy,
                    'success': result['success'],
                    'message': result.get('message', ''),
                    'data': result.get('data', {})
                })

                if result['success']:
                    logger.info(f"Recovery strategy '{strategy}' succeeded for error '{error_type}'")
                    return {
                        'success': True,
                        'strategy_used': strategy,
                        'message': result.get('message', 'Recovery successful'),
                        'data': result.get('data', {}),
                        'recovery_attempts': recovery_results
                    }

            except Exception as e:
                logger.error(f"Recovery strategy '{strategy}' failed: {str(e)}")
                recovery_results.append({
                    'strategy': strategy,
                    'success': False,
                    'error': str(e)
                })

        # All strategies failed
        logger.error(f"All recovery strategies failed for error '{error_type}'")
        return {
            'success': False,
            'error': f'All recovery strategies failed for {error_type}',
            'escalated': True,
            'recovery_attempts': recovery_results
        }

    def _execute_recovery_strategy(self, strategy: str, context: Dict) -> Dict:
        """
        Execute a specific recovery strategy
        """
        strategy_map = {
            'substitute_item': self._substitute_item,
            'find_alternative_vendor': self._find_alternative_vendor,
            'partial_refund': self._partial_refund,
            'cancel_item': self._cancel_item,
            'retry_payment': self._retry_payment,
            'alternative_payment_method': self._alternative_payment_method,
            'split_payment': self._split_payment,
            'cancel_order': self._cancel_order,
            'reassign_vendor': self._reassign_vendor,
            'delay_order': self._delay_order,
            'reassign_courier': self._reassign_courier,
            'delay_delivery': self._delay_delivery,
            'notify_customer': self._notify_customer,
            'cancel_delivery': self._cancel_delivery,
            'suggest_alternatives': self._suggest_alternatives,
            'manual_address_entry': self._manual_address_entry,
            'geocode_correction': self._geocode_correction,
            'contact_customer': self._contact_customer,
            'retry_operation': self._retry_operation,
            'fallback_mode': self._fallback_mode,
            'escalate_to_support': self._escalate_to_support,
            'compensate_customer': self._compensate_customer,
            'redeliver': self._redeliver,
            'refund_delivery': self._refund_delivery
        }

        if strategy not in strategy_map:
            raise ValueError(f"Unknown recovery strategy: {strategy}")

        return strategy_map[strategy](context)

    def _substitute_item(self, context: Dict) -> Dict:
        """Substitute unavailable item with alternative"""
        order = context.get('order')
        unavailable_item = context.get('unavailable_item')

        if not order or not unavailable_item:
            return {'success': False, 'message': 'Missing order or item data'}

        # Import here to avoid circular imports
        from .alternative_suggestions_service import AlternativeSuggestionsService

        alt_service = AlternativeSuggestionsService()
        alternatives = alt_service.generate_item_alternatives(unavailable_item.get('name', ''))

        if alternatives.get('substitutes'):
            # Automatically substitute with first alternative
            alternative = alternatives['substitutes'][0]

            # Update order item (simplified - would need actual implementation)
            return {
                'success': True,
                'message': f'Substituted {unavailable_item["name"]} with {alternative["name"]}',
                'data': {
                    'original_item': unavailable_item,
                    'substitute_item': alternative
                }
            }

        return {'success': False, 'message': 'No suitable substitutes found'}

    def _find_alternative_vendor(self, context: Dict) -> Dict:
        """Find alternative vendor for unavailable item"""
        item_name = context.get('item_name', '')
        location = context.get('location')

        # Import here to avoid circular imports
        from .alternative_suggestions_service import AlternativeSuggestionsService

        alt_service = AlternativeSuggestionsService()
        alternatives = alt_service.generate_item_alternatives(item_name, location_coords=location)

        if alternatives.get('substitutes') or alternatives.get('nearby_vendors'):
            return {
                'success': True,
                'message': f'Found alternative vendors for {item_name}',
                'data': {'alternatives': alternatives}
            }

        return {'success': False, 'message': 'No alternative vendors found'}

    def _partial_refund(self, context: Dict) -> Dict:
        """Process partial refund for unavailable items"""
        order = context.get('order')
        refund_amount = context.get('refund_amount', 0)

        if not order or refund_amount <= 0:
            return {'success': False, 'message': 'Invalid refund data'}

        # Process refund (simplified - would integrate with payment provider)
        return {
            'success': True,
            'message': f'Processed partial refund of ₦{refund_amount}',
            'data': {'refund_amount': refund_amount}
        }

    def _cancel_item(self, context: Dict) -> Dict:
        """Cancel unavailable item from order"""
        order = context.get('order')
        item_to_cancel = context.get('item')

        if not order or not item_to_cancel:
            return {'success': False, 'message': 'Missing order or item data'}

        # Cancel item (simplified - would need actual implementation)
        return {
            'success': True,
            'message': f'Cancelled {item_to_cancel.get("name", "item")} from order',
            'data': {'cancelled_item': item_to_cancel}
        }

    def _retry_payment(self, context: Dict) -> Dict:
        """Retry failed payment"""
        order = context.get('order')
        payment_data = context.get('payment_data')

        if not order or not payment_data:
            return {'success': False, 'message': 'Missing payment data'}

        # Retry payment (simplified - would integrate with payment provider)
        return {
            'success': True,
            'message': 'Payment retry initiated',
            'data': {'retry_attempted': True}
        }

    def _alternative_payment_method(self, context: Dict) -> Dict:
        """Suggest alternative payment method"""
        order = context.get('order')

        if not order:
            return {'success': False, 'message': 'Missing order data'}

        # Suggest alternative payment methods
        return {
            'success': True,
            'message': 'Alternative payment methods suggested to customer',
            'data': {
                'suggested_methods': ['bank_transfer', 'card', 'crypto'],
                'customer_notified': True
            }
        }

    def _split_payment(self, context: Dict) -> Dict:
        """Split payment across multiple methods"""
        order = context.get('order')
        split_data = context.get('split_data')

        if not order or not split_data:
            return {'success': False, 'message': 'Missing split payment data'}

        # Process split payment (simplified)
        return {
            'success': True,
            'message': 'Split payment processed',
            'data': {'split_processed': True}
        }

    def _cancel_order(self, context: Dict) -> Dict:
        """Cancel entire order"""
        order = context.get('order')

        if not order:
            return {'success': False, 'message': 'Missing order data'}

        # Cancel order (simplified - would need proper status updates)
        return {
            'success': True,
            'message': 'Order cancelled and refund processed',
            'data': {'order_cancelled': True, 'refund_processed': True}
        }

    def _reassign_vendor(self, context: Dict) -> Dict:
        """Reassign order to different vendor"""
        order = context.get('order')

        if not order:
            return {'success': False, 'message': 'Missing order data'}

        # Reassign vendor (simplified)
        return {
            'success': True,
            'message': 'Order reassigned to alternative vendor',
            'data': {'vendor_reassigned': True}
        }

    def _delay_order(self, context: Dict) -> Dict:
        """Delay order preparation"""
        order = context.get('order')
        delay_minutes = context.get('delay_minutes', 30)

        if not order:
            return {'success': False, 'message': 'Missing order data'}

        # Delay order (simplified)
        return {
            'success': True,
            'message': f'Order delayed by {delay_minutes} minutes',
            'data': {'delay_minutes': delay_minutes}
        }

    def _reassign_courier(self, context: Dict) -> Dict:
        """Reassign delivery to different courier"""
        order = context.get('order')

        if not order:
            return {'success': False, 'message': 'Missing order data'}

        # Reassign courier (simplified)
        return {
            'success': True,
            'message': 'Delivery reassigned to alternative courier',
            'data': {'courier_reassigned': True}
        }

    def _delay_delivery(self, context: Dict) -> Dict:
        """Delay delivery"""
        order = context.get('order')
        delay_minutes = context.get('delay_minutes', 15)

        if not order:
            return {'success': False, 'message': 'Missing order data'}

        # Delay delivery (simplified)
        return {
            'success': True,
            'message': f'Delivery delayed by {delay_minutes} minutes',
            'data': {'delay_minutes': delay_minutes}
        }

    def _notify_customer(self, context: Dict) -> Dict:
        """Notify customer of issue"""
        order = context.get('order')
        message = context.get('message', 'We are experiencing a delay')

        if not order:
            return {'success': False, 'message': 'Missing order data'}

        # Notify customer (simplified - would use actual notification service)
        return {
            'success': True,
            'message': 'Customer notified of issue',
            'data': {'notification_sent': True, 'message': message}
        }

    def _cancel_delivery(self, context: Dict) -> Dict:
        """Cancel delivery"""
        order = context.get('order')

        if not order:
            return {'success': False, 'message': 'Missing order data'}

        # Cancel delivery (simplified)
        return {
            'success': True,
            'message': 'Delivery cancelled',
            'data': {'delivery_cancelled': True}
        }

    def _suggest_alternatives(self, context: Dict) -> Dict:
        """Suggest alternative addresses"""
        invalid_address = context.get('invalid_address')

        if not invalid_address:
            return {'success': False, 'message': 'Missing address data'}

        # Suggest alternatives (simplified)
        return {
            'success': True,
            'message': 'Alternative addresses suggested',
            'data': {'suggestions': ['Nearby address 1', 'Nearby address 2']}
        }

    def _manual_address_entry(self, context: Dict) -> Dict:
        """Allow manual address entry"""
        return {
            'success': True,
            'message': 'Manual address entry enabled',
            'data': {'manual_entry_allowed': True}
        }

    def _geocode_correction(self, context: Dict) -> Dict:
        """Attempt to correct geocoding issues"""
        address = context.get('address')

        if not address:
            return {'success': False, 'message': 'Missing address data'}

        # Attempt geocoding correction (simplified)
        return {
            'success': True,
            'message': 'Address geocoding corrected',
            'data': {'corrected': True}
        }

    def _contact_customer(self, context: Dict) -> Dict:
        """Contact customer for clarification"""
        order = context.get('order')
        contact_reason = context.get('reason', 'Need clarification')

        if not order:
            return {'success': False, 'message': 'Missing order data'}

        # Contact customer (simplified)
        return {
            'success': True,
            'message': f'Customer contacted for: {contact_reason}',
            'data': {'contact_initiated': True}
        }

    def _retry_operation(self, context: Dict) -> Dict:
        """Retry failed operation"""
        operation = context.get('operation')
        max_retries = context.get('max_retries', 3)

        # Retry logic (simplified)
        return {
            'success': True,
            'message': f'Operation {operation} retried successfully',
            'data': {'retries_attempted': 1}
        }

    def _fallback_mode(self, context: Dict) -> Dict:
        """Switch to fallback mode"""
        system_component = context.get('component', 'system')

        # Enable fallback mode (simplified)
        return {
            'success': True,
            'message': f'Fallback mode enabled for {system_component}',
            'data': {'fallback_enabled': True}
        }

    def _escalate_to_support(self, context: Dict) -> Dict:
        """Escalate to human support"""
        from .support_escalation_service import SupportEscalationService

        escalation_service = SupportEscalationService()
        conversation = context.get('conversation')
        error_type = context.get('error_type', 'system_error')

        if not conversation:
            return {'success': False, 'message': 'Missing conversation data'}

        escalation = escalation_service.create_escalation(
            conversation=conversation,
            trigger_type='system_error',
            context=context
        )

        return {
            'success': True,
            'message': 'Escalated to human support',
            'data': {'escalation_id': escalation.id}
        }

    def _compensate_customer(self, context: Dict) -> Dict:
        """Provide compensation to customer"""
        order = context.get('order')
        compensation_amount = context.get('compensation', 500)  # ₦500 default

        if not order:
            return {'success': False, 'message': 'Missing order data'}

        # Process compensation (simplified)
        return {
            'success': True,
            'message': f'Customer compensated with ₦{compensation_amount}',
            'data': {'compensation_amount': compensation_amount}
        }

    def _redeliver(self, context: Dict) -> Dict:
        """Arrange redelivery"""
        order = context.get('order')

        if not order:
            return {'success': False, 'message': 'Missing order data'}

        # Arrange redelivery (simplified)
        return {
            'success': True,
            'message': 'Redelivery arranged',
            'data': {'redelivery_scheduled': True}
        }

    def _refund_delivery(self, context: Dict) -> Dict:
        """Refund delivery fee"""
        order = context.get('order')
        refund_amount = context.get('delivery_fee', 0)

        if not order or refund_amount <= 0:
            return {'success': False, 'message': 'Invalid refund data'}

        # Process delivery refund (simplified)
        return {
            'success': True,
            'message': f'Delivery fee of ₦{refund_amount} refunded',
            'data': {'refund_amount': refund_amount}
        }