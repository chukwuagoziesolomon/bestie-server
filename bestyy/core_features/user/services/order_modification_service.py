"""
Order modification service for handling order changes after placement
"""
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from ..models import Order, OrderItem, MenuItem, OrderModification

logger = logging.getLogger(__name__)


class OrderModificationService:
    """
    Service for handling order modifications like adding/removing items,
    changing quantities, substituting items, etc.
    """

    ALLOWED_MODIFICATION_STATUSES = ['awaiting', 'pending', 'payment_confirmed']

    def __init__(self):
        self.modification_history = {}

    def validate_modification_request(self, order: Order, modification_type: str,
                                    modification_data: Dict) -> Tuple[bool, str]:
        """
        Validate if a modification request is allowed
        """
        # Check order status
        if order.status not in self.ALLOWED_MODIFICATION_STATUSES:
            return False, f"Order cannot be modified at status '{order.status}'. Modifications are only allowed for orders in {', '.join(self.ALLOWED_MODIFICATION_STATUSES)} status."

        # Check modification type
        allowed_types = ['add_item', 'remove_item', 'change_quantity', 'substitute_item', 'change_address']
        if modification_type not in allowed_types:
            return False, f"Modification type '{modification_type}' is not supported."

        # Type-specific validation
        if modification_type == 'add_item':
            return self._validate_add_item(order, modification_data)
        elif modification_type == 'remove_item':
            return self._validate_remove_item(order, modification_data)
        elif modification_type == 'change_quantity':
            return self._validate_change_quantity(order, modification_data)
        elif modification_type == 'substitute_item':
            return self._validate_substitute_item(order, modification_data)
        elif modification_type == 'change_address':
            return self._validate_change_address(order, modification_data)

        return True, "Modification request is valid."

    def _validate_add_item(self, order: Order, data: Dict) -> Tuple[bool, str]:
        """Validate adding an item to order"""
        menu_item_id = data.get('menu_item_id')
        quantity = data.get('quantity', 1)

        if not menu_item_id:
            return False, "Menu item ID is required."

        try:
            menu_item = MenuItem.objects.get(id=menu_item_id, available_now=True)
        except MenuItem.DoesNotExist:
            return False, "Menu item not found or not available."

        # Check if item is from same vendor (for simplicity, allow cross-vendor for now)
        # In production, you might want to restrict to same vendor or handle multi-vendor

        if quantity < 1:
            return False, "Quantity must be at least 1."

        return True, "Add item validation passed."

    def _validate_remove_item(self, order: Order, data: Dict) -> Tuple[bool, str]:
        """Validate removing an item from order"""
        order_item_id = data.get('order_item_id')

        if not order_item_id:
            return False, "Order item ID is required."

        try:
            order_item = OrderItem.objects.get(id=order_item_id, cart__user=order.user)
        except OrderItem.DoesNotExist:
            return False, "Order item not found."

        # Check if this would leave order empty
        remaining_items = OrderItem.objects.filter(cart__user=order.customer).exclude(id=order_item_id).count()
        if remaining_items == 0:
            return False, "Cannot remove the last item from order. Cancel the order instead."

        return True, "Remove item validation passed."

    def _validate_change_quantity(self, order: Order, data: Dict) -> Tuple[bool, str]:
        """Validate changing item quantity"""
        order_item_id = data.get('order_item_id')
        new_quantity = data.get('new_quantity')

        if not order_item_id:
            return False, "Order item ID is required."

        if new_quantity is None or new_quantity < 1:
            return False, "New quantity must be at least 1."

        try:
            order_item = OrderItem.objects.get(id=order_item_id, cart__user=order.user)
        except OrderItem.DoesNotExist:
            return False, "Order item not found."

        return True, "Change quantity validation passed."

    def _validate_substitute_item(self, order: Order, data: Dict) -> Tuple[bool, str]:
        """Validate substituting an item"""
        order_item_id = data.get('order_item_id')
        new_menu_item_id = data.get('new_menu_item_id')

        if not order_item_id or not new_menu_item_id:
            return False, "Both order item ID and new menu item ID are required."

        try:
            order_item = OrderItem.objects.get(id=order_item_id, cart__user=order.user)
        except OrderItem.DoesNotExist:
            return False, "Order item not found."

        try:
            new_menu_item = MenuItem.objects.get(id=new_menu_item_id, available_now=True)
        except MenuItem.DoesNotExist:
            return False, "New menu item not found or not available."

        return True, "Substitute item validation passed."

    def _validate_change_address(self, order: Order, data: Dict) -> Tuple[bool, str]:
        """Validate changing delivery address"""
        new_address_id = data.get('new_address_id')

        if not new_address_id:
            return False, "New address ID is required."

        # Additional validation could check if address belongs to user
        # and if it's within delivery range

        return True, "Change address validation passed."

    @transaction.atomic
    def apply_modification(self, order: Order, modification_type: str,
                          modification_data: Dict, user=None) -> Tuple[bool, Dict]:
        """
        Apply a validated modification to an order
        """
        # Create modification record
        modification = OrderModification.objects.create(
            original_order=order,
            modification_type=modification_type,
            old_data=self._get_order_snapshot(order),
            new_data=modification_data,
            approved_by_user=True,  # Assuming user approval for now
            approved_by_vendor=False  # Vendor approval might be needed for some changes
        )

        result = {'success': False, 'message': '', 'price_difference': 0.0}

        try:
            if modification_type == 'add_item':
                success, message, price_diff = self._apply_add_item(order, modification_data)
            elif modification_type == 'remove_item':
                success, message, price_diff = self._apply_remove_item(order, modification_data)
            elif modification_type == 'change_quantity':
                success, message, price_diff = self._apply_change_quantity(order, modification_data)
            elif modification_type == 'substitute_item':
                success, message, price_diff = self._apply_substitute_item(order, modification_data)
            elif modification_type == 'change_address':
                success, message, price_diff = self._apply_change_address(order, modification_data)
            else:
                return False, {'success': False, 'message': f'Unknown modification type: {modification_type}'}

            if success:
                # Update modification record
                modification.price_difference = price_diff
                modification.save()

                # Recalculate order total
                self._recalculate_order_total(order)

                result.update({
                    'success': True,
                    'message': message,
                    'price_difference': float(price_diff),
                    'new_total': float(order.total_amount),
                    'modification_id': modification.id
                })
            else:
                result['message'] = message

        except Exception as e:
            logger.error(f"Error applying modification {modification_type}: {str(e)}")
            result['message'] = f"Error applying modification: {str(e)}"

        return result['success'], result

    def _apply_add_item(self, order: Order, data: Dict) -> Tuple[bool, str, Decimal]:
        """Apply adding an item to order"""
        menu_item_id = data['menu_item_id']
        quantity = data.get('quantity', 1)

        menu_item = MenuItem.objects.get(id=menu_item_id)
        price = menu_item.price * quantity

        # Create order item (assuming order has a cart relationship)
        # This is a simplified implementation - adjust based on your actual model structure
        OrderItem.objects.create(
            cart=order,  # Assuming order has cart field
            menu_item=menu_item,
            quantity=quantity,
            price=menu_item.price
        )

        return True, f"Added {quantity}x {menu_item.dish_name} to order", price

    def _apply_remove_item(self, order: Order, data: Dict) -> Tuple[bool, str, Decimal]:
        """Apply removing an item from order"""
        order_item_id = data['order_item_id']

        order_item = OrderItem.objects.get(id=order_item_id)
        price_removed = order_item.price * order_item.quantity

        order_item.delete()

        return True, f"Removed {order_item.menu_item.dish_name} from order", -price_removed

    def _apply_change_quantity(self, order: Order, data: Dict) -> Tuple[bool, str, Decimal]:
        """Apply changing item quantity"""
        order_item_id = data['order_item_id']
        new_quantity = data['new_quantity']

        order_item = OrderItem.objects.get(id=order_item_id)
        old_total = order_item.price * order_item.quantity
        new_total = order_item.price * new_quantity

        order_item.quantity = new_quantity
        order_item.save()

        price_difference = new_total - old_total

        return True, f"Changed {order_item.menu_item.dish_name} quantity to {new_quantity}", price_difference

    def _apply_substitute_item(self, order: Order, data: Dict) -> Tuple[bool, str, Decimal]:
        """Apply substituting an item"""
        order_item_id = data['order_item_id']
        new_menu_item_id = data['new_menu_item_id']

        order_item = OrderItem.objects.get(id=order_item_id)
        new_menu_item = MenuItem.objects.get(id=new_menu_item_id)

        old_price = order_item.price * order_item.quantity
        new_price = new_menu_item.price * order_item.quantity

        # Update the order item
        order_item.menu_item = new_menu_item
        order_item.price = new_menu_item.price
        order_item.save()

        price_difference = new_price - old_price

        return True, f"Substituted {order_item.menu_item.dish_name} with {new_menu_item.dish_name}", price_difference

    def _apply_change_address(self, order: Order, data: Dict) -> Tuple[bool, str, Decimal]:
        """Apply changing delivery address"""
        new_address_id = data['new_address_id']

        # Update order delivery address
        # This assumes you have an Address model and order has delivery_address field
        from ..models import Address
        new_address = Address.objects.get(id=new_address_id, user=order.user)

        order.delivery_address = new_address.full_address
        order.save()

        return True, f"Changed delivery address to {new_address.full_address}", Decimal('0.00')

    def _get_order_snapshot(self, order: Order) -> Dict:
        """Get a snapshot of current order state"""
        items = []
        for item in order.items.all():
            items.append({
                'menu_item_id': item.menu_item.id,
                'menu_item_name': item.menu_item.dish_name,
                'quantity': item.quantity,
                'price': float(item.price),
                'total': float(item.price * item.quantity)
            })

        return {
            'total_amount': float(order.total_amount),
            'delivery_address': order.delivery_address,
            'special_instructions': order.special_instructions,
            'items': items,
            'status': order.status
        }

    def _recalculate_order_total(self, order: Order):
        """Recalculate order total after modifications"""
        # Sum all order items
        items_total = sum(
            item.price * item.quantity
            for item in order.items.all()
        )

        # Add delivery fee
        order.total_amount = items_total + (order.delivery_fee or 0)
        order.save()

    def get_modification_history(self, order: Order) -> List[Dict]:
        """Get modification history for an order"""
        modifications = OrderModification.objects.filter(
            original_order=order
        ).order_by('-created_at')

        history = []
        for mod in modifications:
            history.append({
                'id': mod.id,
                'type': mod.modification_type,
                'timestamp': mod.created_at.isoformat(),
                'price_difference': float(mod.price_difference),
                'approved_by_user': mod.approved_by_user,
                'approved_by_vendor': mod.approved_by_vendor,
                'old_data': mod.old_data,
                'new_data': mod.new_data
            })

        return history

    def can_modify_order(self, order: Order) -> Tuple[bool, str]:
        """Check if an order can be modified"""
        if order.status not in self.ALLOWED_MODIFICATION_STATUSES:
            return False, f"Order status '{order.status}' does not allow modifications."

        # Check time constraints (e.g., can't modify if vendor has started preparing)
        if order.status == 'processing':
            return False, "Order is already being prepared and cannot be modified."

        return True, "Order can be modified."