"""
Test script to verify CORS headers are correctly configured.
"""
import requests
from pprint import pprint

# Test endpoints
BACKEND_URL = "https://bestie-server.onrender.com"
ADMIN_ORIGIN = "https://bestie-admin.vercel.app"

def test_cors_preflight():
    """Test CORS preflight request (OPTIONS)"""
    print("\n" + "="*60)
    print("Testing CORS Preflight (OPTIONS) Request")
    print("="*60)
    
    headers = {
        'Origin': ADMIN_ORIGIN,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'x-cart-token,content-type',
    }
    
    endpoint = f"{BACKEND_URL}/api/user/website-cart/add/"
    
    try:
        response = requests.options(endpoint, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"\nResponse Headers:")
        pprint(dict(response.headers))
        
        # Check critical CORS headers
        print("\n" + "-"*60)
        print("Critical CORS Headers:")
        print("-"*60)
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials'),
        }
        
        for key, value in cors_headers.items():
            status = "✓" if value else "✗"
            print(f"{status} {key}: {value}")
        
        # Validation
        print("\n" + "-"*60)
        print("Validation:")
        print("-"*60)
        
        if cors_headers['Access-Control-Allow-Origin'] == ADMIN_ORIGIN:
            print(f"✓ Admin origin ({ADMIN_ORIGIN}) is allowed")
        elif cors_headers['Access-Control-Allow-Origin'] == '*':
            print(f"⚠ All origins are allowed (not specific)")
        else:
            print(f"✗ Admin origin NOT allowed. Got: {cors_headers['Access-Control-Allow-Origin']}")
        
        if 'x-cart-token' in (cors_headers['Access-Control-Allow-Headers'] or '').lower():
            print("✓ x-cart-token header is allowed")
        else:
            print(f"✗ x-cart-token header NOT allowed. Got: {cors_headers['Access-Control-Allow-Headers']}")
            
        if 'POST' in (cors_headers['Access-Control-Allow-Methods'] or ''):
            print("✓ POST method is allowed")
        else:
            print(f"✗ POST method NOT allowed. Got: {cors_headers['Access-Control-Allow-Methods']}")
        
    except Exception as e:
        print(f"✗ Error: {e}")

def test_actual_request():
    """Test actual POST request with CORS headers"""
    print("\n" + "="*60)
    print("Testing Actual POST Request")
    print("="*60)
    
    headers = {
        'Origin': ADMIN_ORIGIN,
        'Content-Type': 'application/json',
        'X-Cart-Token': 'test-token-12345',
    }
    
    endpoint = f"{BACKEND_URL}/api/user/website-cart/add/"
    
    data = {
        'menu_item_id': 1,
        'quantity': 1
    }
    
    try:
        response = requests.post(endpoint, json=data, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        print(f"\nResponse Headers:")
        pprint(dict(response.headers))
        
        # Check if CORS headers are present in actual response
        print("\n" + "-"*60)
        print("CORS Headers in Response:")
        print("-"*60)
        
        acao = response.headers.get('Access-Control-Allow-Origin')
        acac = response.headers.get('Access-Control-Allow-Credentials')
        
        if acao:
            print(f"✓ Access-Control-Allow-Origin: {acao}")
        else:
            print("✗ Access-Control-Allow-Origin header is MISSING")
        
        if acac:
            print(f"✓ Access-Control-Allow-Credentials: {acac}")
        else:
            print("⚠ Access-Control-Allow-Credentials header is missing")
            
    except Exception as e:
        print(f"✗ Error: {e}")

def test_simple_get():
    """Test simple GET request"""
    print("\n" + "="*60)
    print("Testing Simple GET Request")
    print("="*60)
    
    headers = {
        'Origin': ADMIN_ORIGIN,
    }
    
    endpoint = f"{BACKEND_URL}/api/user/check-session/"
    
    try:
        response = requests.get(endpoint, headers=headers)
        print(f"\nStatus Code: {response.status_code}")
        
        acao = response.headers.get('Access-Control-Allow-Origin')
        if acao:
            print(f"✓ Access-Control-Allow-Origin: {acao}")
        else:
            print("✗ Access-Control-Allow-Origin header is MISSING")
            
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == '__main__':
    print("\nCORS Configuration Test")
    print("="*60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Testing from Origin: {ADMIN_ORIGIN}")
    
    test_simple_get()
    test_cors_preflight()
    test_actual_request()
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
    print("\nIf you see '✗' marks above, those are the issues to fix.")
    print("Share these results to help diagnose the CORS issue.")
