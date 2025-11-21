"""
Test Payment Verification Script
Run this to simulate payment for testing the order flow
"""
import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def list_pending_orders():
    """List all orders awaiting payment"""
    print("\n📋 Fetching pending orders...")
    response = requests.get(f"{BASE_URL}/api/user/payments/test/pending/")
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            orders = data['orders']
            print(f"\n✅ Found {data['count']} pending order(s):\n")
            
            for i, order in enumerate(orders, 1):
                print(f"{i}. Order #{order['order_number']}")
                print(f"   ID: {order['id']}")
                print(f"   Customer: {order['customer']}")
                print(f"   Vendor: {order['vendor']}")
                print(f"   Amount: ₦{order['total_amount']:,.2f}")
                print(f"   Address: {order['delivery_address']}")
                print(f"   Status: {order['status']}")
                print(f"   Items: {order['items_count']}")
                print()
            
            return orders
        else:
            print(f"❌ Error: {data.get('error')}")
            return []
    else:
        print(f"❌ HTTP Error {response.status_code}")
        print(response.text)
        return []


def verify_payment(order_id):
    """Simulate payment verification for an order"""
    print(f"\n💳 Simulating payment verification for order: {order_id}")
    
    response = requests.post(
        f"{BASE_URL}/api/user/payments/test/verify/",
        json={'order_id': order_id}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            order = data['order']
            print("\n✅ Payment verified successfully!\n")
            print(f"Order Number: {order['order_number']}")
            print(f"Status: {order['status']}")
            print(f"Payment Status: {'PAID' if order['payment_status'] else 'UNPAID'}")
            print(f"Total Amount: ₦{order['total_amount']:,.2f}")
            print(f"Pickup Code (for courier): {order['pickup_code']}")
            print(f"Confirmed At: {order['confirmed_at']}")
            print("\n🎉 Order is now confirmed and ready for preparation!")
            return True
        else:
            print(f"\n⚠️ {data.get('message', data.get('error'))}")
            return False
    else:
        print(f"\n❌ HTTP Error {response.status_code}")
        print(response.text)
        return False


def main():
    print("=" * 60)
    print("🧪 PAYMENT VERIFICATION TEST TOOL")
    print("=" * 60)
    
    # List pending orders
    orders = list_pending_orders()
    
    if not orders:
        print("\n⚠️ No pending orders found. Place an order first through WhatsApp!")
        return
    
    # Prompt user to select order
    print("\n" + "=" * 60)
    if len(orders) == 1:
        print(f"💡 Only one pending order found. Using Order ID: {orders[0]['id'][:8]}...")
        selected_order = orders[0]
    else:
        try:
            choice = input(f"\nEnter order number to verify (1-{len(orders)}): ")
            index = int(choice) - 1
            if 0 <= index < len(orders):
                selected_order = orders[index]
            else:
                print("❌ Invalid selection")
                return
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Cancelled")
            return
    
    # Verify payment
    print("\n" + "=" * 60)
    success = verify_payment(selected_order['id'])
    
    if success:
        print("\n" + "=" * 60)
        print("✅ TEST COMPLETE!")
        print("=" * 60)
        print("\n📱 Now check WhatsApp - the order should be confirmed!")
        print("🧑‍🍳 Vendor can start preparing the order")
        print("🚗 Courier can use pickup code to collect the order")
    else:
        print("\n❌ Test failed - check the error messages above")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
