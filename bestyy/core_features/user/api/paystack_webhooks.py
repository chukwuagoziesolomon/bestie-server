from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils import timezone
from bestyy.core_features.user.models import Payment
from bestyy.restaurant_features.order.models import Order
from decimal import Decimal
import json
import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)


def _send_code_notifications(order):
    """
    Send WhatsApp notifications to vendor and courier with pickup/delivery codes
    """
    try:
        from bestyy.communication.whatsapp.services.meta_whatsapp_service import MetaWhatsAppService

        meta_service = MetaWhatsAppService()

        # Send pickup code to vendor
        if order.vendor and order.vendor.user and order.vendor.user.phone:
            vendor_message = (
                f"🍽️ New Order Ready!\n\n"
                f"Order #{order.id} - {order.order_name}\n"
                f"Customer: {order.user.get_full_name() or order.user.email}\n"
                f"Address: {order.delivery_address}\n\n"
                f"🚴 Courier will arrive with pickup code.\n"
                f"Enter the 6-digit code here to confirm pickup and receive payment.\n\n"
                f"Reply with 'help' for more info."
            )

            result = meta_service.send_message(
                to=order.vendor.user.phone,
                message=vendor_message
            )

            if result.get('success'):
                logger.info(f"Pickup code notification sent to vendor {order.vendor.user.phone}")
            else:
                logger.error(f"Failed to send pickup code to vendor: {result.get('message')}")

        # Send delivery OTP to courier (if assigned)
        if order.courier and order.courier.user and order.courier.user.phone:
            courier_message = (
                f"🚴 New Delivery Assignment!\n\n"
                f"Order #{order.id} - {order.order_name}\n"
                f"Pickup: {order.vendor.business_name}\n"
                f"Delivery: {order.delivery_address}\n\n"
                f"📱 Customer will provide delivery OTP.\n"
                f"Enter the 6-digit OTP here to confirm delivery and receive payment.\n\n"
                f"Reply with 'help' for more info."
            )

            result = meta_service.send_message(
                to=order.courier.user.phone,
                message=courier_message
            )

            if result.get('success'):
                logger.info(f"Delivery OTP notification sent to courier {order.courier.user.phone}")
            else:
                logger.error(f"Failed to send delivery OTP to courier: {result.get('message')}")

    except Exception as e:
        logger.error(f"Error sending code notifications: {str(e)}")


def _send_payment_receipt(order):
    """
    Send payment receipt to user, vendor, and courier via WhatsApp
    """
    try:
        from bestyy.communication.whatsapp.services.meta_whatsapp_service import MetaWhatsAppService
        from django.template.loader import render_to_string

        meta_service = MetaWhatsAppService()

        # Prepare receipt data
        items = []
        for order_item in order.items.all():
            items.append({
                'name': order_item.menu_item.dish_name,
                'description': order_item.menu_item.item_description,
                'quantity': order_item.quantity,
                'total_price': float(order_item.price * order_item.quantity),
                'image_url': order_item.menu_item.image.url if order_item.menu_item.image else None
            })

        receipt_data = {
            'order_id': order.id,
            'order_date': order.order_placed_at.strftime('%B %d, %Y at %I:%M %p'),
            'customer_name': f"{order.user.first_name} {order.user.last_name}".strip() or order.user.email,
            'vendor_name': order.vendor.business_name,
            'items': items,
            'subtotal': float(order.total_price),
            'delivery_fee': float(order.delivery_fee),
            'service_fee': 0.0,  # Not implemented yet
            'discount': 0.0,     # Not implemented yet
            'total_amount': float(order.total_price + order.delivery_fee),
            'payment_method': 'Bank Transfer',
            'payment_reference': f"ORDER-{order.id}",
            'delivery_address': order.delivery_address,
            'estimated_delivery': '30-45 minutes'
        }

        # Send receipt to user
        if order.user.phone:
            user_message = f"""🧾 *Payment Receipt - Bestyy*

Order #{order.id}
Date: {receipt_data['order_date']}

📍 *Items Ordered:*
"""
            for item in items:
                user_message += f"• {item['name']} x{item['quantity']} - ₦{item['total_price']:.2f}\n"

            user_message += f"""
💰 *Payment Summary:*
Food Amount: ₦{receipt_data['subtotal']:.2f}
Delivery Fee: ₦{receipt_data['delivery_fee']:.2f}
*Total Paid: ₦{receipt_data['total_amount']:.2f}*

✅ Payment Status: Successful
Method: Bank Transfer
Reference: {receipt_data['payment_reference']}

🚚 Delivery Address: {order.delivery_address}
⏰ Estimated Delivery: 30-45 minutes

Thank you for choosing Bestyy! 🍽️"""

            result = meta_service.send_message(
                to=order.user.phone,
                message=user_message
            )

            if result.get('success'):
                logger.info(f"Payment receipt sent to user {order.user.phone}")
            else:
                logger.error(f"Failed to send receipt to user: {result.get('message')}")

        # Send receipt to vendor
        if order.vendor and order.vendor.user and order.vendor.user.phone:
            vendor_message = f"""💰 *Payment Received - Bestyy*

Order #{order.id} - Payment Confirmed!

📦 *Order Details:*
"""
            for item in items:
                vendor_message += f"• {item['name']} x{item['quantity']} - ₦{item['total_price']:.2f}\n"

            payouts = order.calculate_payouts()
            vendor_message += f"""
💵 *Your Earnings:*
Food Amount: ₦{receipt_data['subtotal']:.2f}
Platform Commission: ₦{payouts['platform_commission']:.2f}
*You'll Receive: ₦{payouts['vendor_amount']:.2f}*

✅ Payment will be transferred to your account once courier confirms pickup.

🚚 Delivery Address: {order.delivery_address}
👤 Customer: {receipt_data['customer_name']}

Please prepare the order for pickup! 🍽️"""

            result = meta_service.send_message(
                to=order.vendor.user.phone,
                message=vendor_message
            )

            if result.get('success'):
                logger.info(f"Payment receipt sent to vendor {order.vendor.user.phone}")
            else:
                logger.error(f"Failed to send receipt to vendor: {result.get('message')}")

        # Send receipt to courier
        if order.courier and order.courier.user and order.courier.user.phone:
            courier_message = f"""🚴 *New Delivery Assignment - Bestyy*

Order #{order.id} - Payment Confirmed!

📦 *Delivery Details:*
"""
            for item in items:
                courier_message += f"• {item['name']} x{item['quantity']}\n"

            payouts = order.calculate_payouts()
            courier_message += f"""
💵 *Your Earnings:*
Delivery Fee: ₦{payouts['courier_amount']:.2f}

✅ Payment will be transferred once you confirm delivery to customer.

🏪 Pickup: {order.vendor.business_name}
🚚 Delivery: {order.delivery_address}
👤 Customer: {receipt_data['customer_name']}

Please coordinate pickup with the vendor! 📱"""

            result = meta_service.send_message(
                to=order.courier.user.phone,
                message=courier_message
            )

            if result.get('success'):
                logger.info(f"Payment receipt sent to courier {order.courier.user.phone}")
            else:
                logger.error(f"Failed to send receipt to courier: {result.get('message')}")

    except Exception as e:
        logger.error(f"Error sending payment receipts: {str(e)}")


def verify_paystack_signature(request):
    """
    Verify Paystack webhook signature
    """
    paystack_signature = request.headers.get('X-Paystack-Signature')
    if not paystack_signature:
        return False

    # Get the raw request body
    body = request.body.decode('utf-8')

    # Create expected signature
    secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
    expected_signature = hmac.new(secret, body.encode('utf-8'), hashlib.sha512).hexdigest()

    return hmac.compare_digest(paystack_signature, expected_signature)


@api_view(['POST'])
@permission_classes([AllowAny])
def paystack_webhook(request):
    """
    Handle Paystack webhooks for payment events
    """
    # Verify webhook signature (in production, always verify)
    if not settings.DEBUG and not verify_paystack_signature(request):
        logger.warning("Invalid Paystack webhook signature")
        return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        event = payload.get('event')
        data = payload.get('data', {})

        logger.info(f"Paystack webhook received: {event}")

        # Handle different event types
        if event == 'charge.success':
            return handle_charge_success(data)
        elif event == 'dedicatedaccount.assign.success':
            return handle_dva_assignment_success(data)
        elif event == 'dedicatedaccount.assign.failed':
            return handle_dva_assignment_failed(data)
        elif event == 'customeridentification.success':
            return handle_customer_identification_success(data)
        elif event == 'customeridentification.failed':
            return handle_customer_identification_failed(data)
        elif event == 'transfer.success':
            return handle_transfer_success(data)
        elif event == 'transfer.failed':
            return handle_transfer_failed(data)
        elif event == 'transfer.reversed':
            return handle_transfer_reversed(data)
        elif event == 'subscription.create':
            return handle_subscription_create(data)
        elif event == 'subscription.disable':
            return handle_subscription_disable(data)
        elif event == 'invoice.create':
            return handle_invoice_create(data)
        elif event == 'invoice.payment_failed':
            return handle_invoice_payment_failed(data)
        elif event == 'invoice.update':
            return handle_invoice_update(data)
        else:
            logger.info(f"Unhandled Paystack event: {event}")
            return Response({'status': 'ignored'})

    except json.JSONDecodeError:
        logger.error("Invalid JSON in Paystack webhook")
        return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error processing Paystack webhook: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_charge_success(data):
    """
    Handle successful charge (payment received)
    """
    try:
        # Extract payment details
        amount = data.get('amount', 0) / 100  # Convert from kobo to naira
        reference = data.get('reference')
        authorization = data.get('authorization', {})
        metadata = data.get('metadata', {})

        # Check if this is an order payment (new conditional payment flow)
        if reference.startswith('order_'):
            # Extract order ID from reference
            try:
                parts = reference.split('_')
                if len(parts) >= 2:
                    order_id = int(parts[1])

                    # Get the order
                    order = Order.objects.get(id=order_id)

                    # Confirm payment
                    order.confirm_payment()

                    # Store payout amounts from metadata
                    if 'vendor_amount' in metadata:
                        order.vendor_payout_amount = Decimal(str(metadata['vendor_amount']))
                    if 'courier_amount' in metadata:
                        order.courier_payout_amount = Decimal(str(metadata['courier_amount']))
                    if 'platform_commission' in metadata:
                        order.platform_commission = Decimal(str(metadata['platform_commission']))

                    order.save()

                    # Generate codes for conditional payouts
                    order.generate_pickup_code()
                    order.generate_delivery_otp()

                    # Send WhatsApp notifications to vendor and courier
                    _send_code_notifications(order)

                    # Send receipt to user
                    _send_payment_receipt(order)

                    # Broadcast payment confirmation via WebSocket
                    from bestyy.core_features.user.services.order_status_broadcast_service import OrderStatusBroadcastService
                    OrderStatusBroadcastService.broadcast_payment_confirmed(order)

                    # Notify vendor about new order
                    from bestyy.core_features.user.services.vendor_order_notification_service import VendorOrderNotificationService
                    VendorOrderNotificationService.notify_vendor_new_order(order)

                    # Find and assign nearby courier
                    from bestyy.core_features.user.services.courier_location_service import CourierLocationService
                    try:
                        # Get delivery location coordinates (you'll need to geocode the address)
                        # For now, using Lagos coordinates as example - replace with actual geocoding
                        delivery_lat = 6.5244  # Lagos latitude
                        delivery_lon = 3.3792  # Lagos longitude

                        # Find nearby couriers
                        nearby_couriers = CourierLocationService.find_nearby_couriers(
                            delivery_lat, delivery_lon,
                            max_distance_km=15.0,
                            max_results=3,
                            require_active=True,
                            require_verified=True
                        )

                        if nearby_couriers:
                            # Assign the closest courier
                            closest_courier, distance = nearby_couriers[0]
                            order.courier = closest_courier
                            order.save()

                            logger.info(f"Assigned courier {closest_courier.id} to order {order.id} (distance: {distance:.2f}km)")

                            # Send notification to assigned courier
                            _send_code_notifications(order)

                            # Broadcast courier assignment via WebSocket
                            OrderStatusBroadcastService.broadcast_new_delivery_request(order, nearby_couriers)
                        else:
                            logger.warning(f"No nearby couriers found for order {order.id}")

                    except Exception as e:
                        logger.error(f"Error assigning courier to order {order.id}: {str(e)}")

                    logger.info(f"Order payment confirmed: Order #{order.id}, amount: ₦{amount}")

            except (ValueError, Order.DoesNotExist) as e:
                logger.error(f"Failed to process order payment: {reference} - {str(e)}")

        # Check if this is a dedicated virtual account payment (legacy)
        elif authorization.get('channel') == 'dedicated_nuban':
            account_number = authorization.get('receiver_bank_account_number')
            sender_name = authorization.get('sender_name')
            sender_bank = authorization.get('sender_bank')
            sender_account = authorization.get('sender_bank_account_number')

            # Find the DVA and associated user
            try:
                dva = DedicatedVirtualAccount.objects.get(
                    account_number=account_number,
                    is_active=True
                )
                user = dva.user

                # Create payment record
                payment = Payment.objects.create(
                    user=user,
                    amount=amount,
                    currency='NGN',
                    payment_method='bank_transfer',
                    paystack_reference=reference,
                    paystack_transaction_id=data.get('id'),
                    status='successful',
                    description=f'Bank transfer from {sender_name} ({sender_bank})',
                    metadata={
                        'sender_name': sender_name,
                        'sender_bank': sender_bank,
                        'sender_account': sender_account,
                        'receiver_account': account_number,
                        'channel': 'dedicated_nuban'
                    }
                )

                logger.info(f"Payment recorded: {payment.id} for user {user.id}, amount: ₦{amount}")

            except DedicatedVirtualAccount.DoesNotExist:
                logger.warning(f"DVA not found for account number: {account_number}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling charge success: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_dva_assignment_success(data):
    """
    Handle successful DVA assignment
    """
    try:
        customer_id = data.get('customer', {}).get('customer_code')

        # Find user by customer ID
        try:
            dva = DedicatedVirtualAccount.objects.get(paystack_customer_id=customer_id)
            dva.is_assigned = True
            dva.is_active = True
            dva.save()

            logger.info(f"DVA assignment successful for user {dva.user.id}")

        except DedicatedVirtualAccount.DoesNotExist:
            logger.warning(f"DVA not found for customer ID: {customer_id}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling DVA assignment success: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_dva_assignment_failed(data):
    """
    Handle failed DVA assignment
    """
    try:
        customer_id = data.get('customer', {}).get('customer_code')
        reason = data.get('reason', 'Unknown reason')

        # Find user by customer ID and mark as failed
        try:
            dva = DedicatedVirtualAccount.objects.get(paystack_customer_id=customer_id)
            dva.is_assigned = False
            dva.is_active = False
            dva.save()

            logger.warning(f"DVA assignment failed for user {dva.user.id}: {reason}")

        except DedicatedVirtualAccount.DoesNotExist:
            logger.warning(f"DVA not found for customer ID: {customer_id}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling DVA assignment failed: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_customer_identification_success(data):
    """
    Handle successful customer identification
    """
    try:
        customer_id = data.get('customer_id')

        # Log successful identification
        logger.info(f"Customer identification successful for customer: {customer_id}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling customer identification success: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_customer_identification_failed(data):
    """
    Handle failed customer identification
    """
    try:
        customer_id = data.get('customer_id')
        reason = data.get('reason', 'Unknown reason')

        # Log failed identification
        logger.warning(f"Customer identification failed for customer {customer_id}: {reason}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling customer identification failed: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_transfer_success(data):
    """
    Handle successful transfer (payout completed)
    """
    try:
        transfer_code = data.get('transfer_code')
        reference = data.get('reference')
        amount = data.get('amount', 0) / 100  # Convert from kobo to naira

        # Find and update transfer record
        try:
            from bestyy.core_features.user.models import Transfer
            transfer = Transfer.objects.get(paystack_reference=reference)
            transfer.status = 'success'
            transfer.completed_at = timezone.now()
            transfer.save()

            logger.info(f"Transfer successful: {reference} - ₦{amount} to {transfer.recipient}")

        except Transfer.DoesNotExist:
            logger.warning(f"Transfer record not found for reference: {reference}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling transfer success: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_transfer_failed(data):
    """
    Handle failed transfer
    """
    try:
        transfer_code = data.get('transfer_code')
        reference = data.get('reference')
        reason = data.get('reason', 'Unknown reason')

        # Find and update transfer record
        try:
            from bestyy.core_features.user.models import Transfer
            transfer = Transfer.objects.get(paystack_reference=reference)
            transfer.status = 'failed'
            transfer.failure_reason = reason
            transfer.save()

            logger.warning(f"Transfer failed: {reference} - Reason: {reason}")

        except Transfer.DoesNotExist:
            logger.warning(f"Transfer record not found for reference: {reference}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling transfer failed: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_transfer_reversed(data):
    """
    Handle reversed transfer (refund)
    """
    try:
        transfer_code = data.get('transfer_code')
        reference = data.get('reference')
        reason = data.get('reason', 'Unknown reason')

        # Find and update transfer record
        try:
            from bestyy.core_features.user.models import Transfer
            transfer = Transfer.objects.get(paystack_reference=reference)
            transfer.status = 'reversed'
            transfer.failure_reason = f"Reversed: {reason}"
            transfer.save()

            logger.warning(f"Transfer reversed: {reference} - Reason: {reason}")

        except Transfer.DoesNotExist:
            logger.warning(f"Transfer record not found for reference: {reference}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling transfer reversed: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_subscription_create(data):
    """
    Handle subscription creation
    """
    try:
        subscription_code = data.get('subscription_code')
        customer_code = data.get('customer', {}).get('customer_code')
        plan_code = data.get('plan', {}).get('plan_code')

        logger.info(f"Subscription created: {subscription_code} for customer {customer_code}")

        # Find vendor by customer code and create/update subscription record
        try:
            from bestyy.core_features.user.models import VendorSubscription, VendorProfile, SubscriptionPlan

            # Find vendor by customer code (this might need adjustment based on how you store customer codes)
            # For now, we'll assume we can find it through the subscription data
            # You might need to store customer_code in VendorSubscription model

            # This is a placeholder - you'll need to implement the logic to find the vendor
            # based on the customer_code or other identifying information

            logger.info(f"Subscription creation handled for: {subscription_code}")

        except Exception as e:
            logger.error(f"Error updating subscription record: {str(e)}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling subscription create: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_subscription_disable(data):
    """
    Handle subscription disable/cancellation
    """
    try:
        subscription_code = data.get('subscription_code')

        logger.info(f"Subscription disabled: {subscription_code}")

        # Find and update subscription record
        try:
            from bestyy.core_features.user.models import VendorSubscription

            subscription = VendorSubscription.objects.get(paystack_subscription_code=subscription_code)
            subscription.cancel_subscription()

            # Remove featured status
            vendor = subscription.vendor
            vendor.is_featured = False
            vendor.featured_priority = 0
            vendor.save()

            logger.info(f"Subscription cancelled for vendor {vendor.id}")

        except VendorSubscription.DoesNotExist:
            logger.warning(f"Subscription not found: {subscription_code}")
        except Exception as e:
            logger.error(f"Error updating subscription: {str(e)}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling subscription disable: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_invoice_create(data):
    """
    Handle invoice creation (subscription payment attempt)
    """
    try:
        subscription_code = data.get('subscription', {}).get('subscription_code')
        invoice_code = data.get('invoice_code')
        amount = data.get('amount', 0) / 100  # Convert from kobo

        logger.info(f"Invoice created: {invoice_code} for subscription {subscription_code}, amount: ₦{amount}")

        # Update subscription next payment date if available
        try:
            from bestyy.core_features.user.models import VendorSubscription

            subscription = VendorSubscription.objects.get(paystack_subscription_code=subscription_code)
            # Update next payment date from invoice data if available
            # This might require additional logic based on Paystack's invoice structure

        except VendorSubscription.DoesNotExist:
            logger.warning(f"Subscription not found for invoice: {subscription_code}")
        except Exception as e:
            logger.error(f"Error updating subscription for invoice: {str(e)}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling invoice create: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_invoice_payment_failed(data):
    """
    Handle failed subscription payment
    """
    try:
        subscription_code = data.get('subscription', {}).get('subscription_code')
        invoice_code = data.get('invoice_code')
        reason = data.get('description', 'Payment failed')

        logger.warning(f"Invoice payment failed: {invoice_code} for subscription {subscription_code} - {reason}")

        # Update subscription status to attention
        try:
            from bestyy.core_features.user.models import VendorSubscription

            subscription = VendorSubscription.objects.get(paystack_subscription_code=subscription_code)
            subscription.status = 'attention'
            subscription.save()

            logger.info(f"Subscription {subscription_code} marked as attention due to payment failure")

        except VendorSubscription.DoesNotExist:
            logger.warning(f"Subscription not found for failed invoice: {subscription_code}")
        except Exception as e:
            logger.error(f"Error updating subscription for failed payment: {str(e)}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling invoice payment failed: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def handle_invoice_update(data):
    """
    Handle invoice update (payment status change)
    """
    try:
        subscription_code = data.get('subscription', {}).get('subscription_code')
        invoice_code = data.get('invoice_code')
        paid = data.get('paid', False)

        if paid:
            logger.info(f"Invoice payment successful: {invoice_code} for subscription {subscription_code}")

            # Update subscription status back to active if it was in attention
            try:
                from bestyy.core_features.user.models import VendorSubscription

                subscription = VendorSubscription.objects.get(paystack_subscription_code=subscription_code)
                if subscription.status == 'attention':
                    subscription.status = 'active'
                    subscription.save()

                    logger.info(f"Subscription {subscription_code} reactivated after successful payment")

            except VendorSubscription.DoesNotExist:
                logger.warning(f"Subscription not found for successful invoice: {subscription_code}")
            except Exception as e:
                logger.error(f"Error updating subscription for successful payment: {str(e)}")
        else:
            logger.info(f"Invoice updated (not paid): {invoice_code} for subscription {subscription_code}")

        return Response({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling invoice update: {str(e)}")
        return Response({'error': 'Processing error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)