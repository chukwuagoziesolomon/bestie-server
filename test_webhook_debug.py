import requests

def test_webhook():
    # Test URLs
    urls = [
        'http://localhost:8000/api/whatsapp/webhook/',
        'https://b0f7539975a9.ngrok-free.app/api/whatsapp/webhook/'
    ]
    
    params = {
        'hub.mode': 'subscribe',
        'hub.challenge': '1234567',
        'hub.verify_token': '_EPmQOB2Fxjln47xEhmXPBurta2Q_biBfIOoW5BW2wE'
    }
    
    headers = {
        'User-Agent': 'WhatsApp/Webhook-Test',
        'Accept': 'text/plain'
    }
    
    for url in urls:
        print(f"\nTesting URL: {url}")
        try:
            response = requests.get(url, params=params, headers=headers)
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Content: {response.text[:200]}")  # First 200 chars only
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == '__main__':
    test_webhook()