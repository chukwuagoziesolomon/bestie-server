"""
Test script for Banner System API
Tests GET endpoint for retrieving banners
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_banner_get_endpoint():
    """Test GET /api/user/banners/ endpoint"""
    print("=" * 60)
    print("TESTING BANNER SYSTEM")
    print("=" * 60)
    
    # Test 1: Get all banners (public endpoint)
    print("\n1. Testing GET /api/user/banners/")
    try:
        response = requests.get(f"{BASE_URL}/api/user/banners/")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS")
            print(f"Response Structure:")
            print(f"  - success: {data.get('success')}")
            print(f"  - count: {data.get('count')}")
            print(f"  - banner_type: {data.get('banner_type')}")
            print(f"  - banners: {len(data.get('banners', []))} items")
            
            if data.get('banners'):
                print(f"\nFirst banner details:")
                banner = data['banners'][0]
                for key, value in banner.items():
                    print(f"  - {key}: {value}")
            else:
                print(f"\n⚠️  No banners found (database is empty)")
                print(f"   You can create banners via:")
                print(f"   - Django Admin: http://localhost:8000/admin/")
                print(f"   - POST API: /api/user/banners/ (requires admin auth)")
        else:
            print(f"❌ FAILED")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    # Test 2: Get banners with limit
    print("\n2. Testing GET /api/user/banners/?limit=5")
    try:
        response = requests.get(f"{BASE_URL}/api/user/banners/?limit=5")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS - Limited to {data.get('count')} banners")
        else:
            print(f"❌ FAILED")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    # Test 3: Get banners by type
    print("\n3. Testing GET /api/user/banners/?type=homepage")
    try:
        response = requests.get(f"{BASE_URL}/api/user/banners/?type=homepage")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS - Found {data.get('count')} homepage banners")
            print(f"Filter applied: {data.get('banner_type')}")
        else:
            print(f"❌ FAILED")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    print("\n" + "=" * 60)
    print("BANNER API ENDPOINTS:")
    print("=" * 60)
    print("\n📌 PUBLIC ENDPOINTS:")
    print("  GET  /api/user/banners/           - Get all active banners")
    print("  GET  /api/user/banners/?limit=N   - Limit results")
    print("  GET  /api/user/banners/?type=X    - Filter by type")
    print("  GET  /api/user/banners/{id}/      - Get banner details")
    
    print("\n🔐 ADMIN ENDPOINTS (requires authentication):")
    print("  POST   /api/user/banners/         - Upload new banner")
    print("  PUT    /api/user/banners/{id}/    - Update banner")
    print("  DELETE /api/user/banners/{id}/    - Delete banner")
    
    print("\n📋 Banner Types:")
    print("  - homepage")
    print("  - promotional")
    print("  - seasonal")
    print("  - vendor_spotlight")
    
    print("\n💡 FRONTEND INTEGRATION:")
    print("""
    // Fetch banners for slideshow
    const response = await fetch('https://bestie-server.onrender.com/api/user/banners/?limit=5');
    const data = await response.json();
    
    if (data.success) {
        const banners = data.banners;
        // banners is an array with:
        // - id
        // - title
        // - description
        // - image_url (optimized 1180x192)
        // - thumbnail_url (for admin preview)
        // - banner_type
        // - priority (for ordering)
        // - click_url (optional redirect)
        // - created_at
    }
    """)
    print("=" * 60)

if __name__ == "__main__":
    test_banner_get_endpoint()
