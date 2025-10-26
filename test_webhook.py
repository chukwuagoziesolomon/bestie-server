import requests

def test_webhook():
    # Your verify token
    verify_token = '_EPmQOB2Fxjln47xEhmXPBurta2Q_biBfIOoW5BW2wE'
    
    # Test both local and ngrok URLs
    urls = [
        'http://localhost:8000/api/whatsapp/webhook/',
        'https://1524681c08e8.ngrok-free.app/api/whatsapp/webhook/'
    ]
    
    for url in urls:
        print(f"\nTesting URL: {url}")
        
        # Test GET request (verification)
        params = {
            'hub.mode': 'subscribe',
            'hub.challenge': '1234567',
            'hub.verify_token': verify_token
        }
        
        try:
            response = requests.get(url, params=params)
            print(f"Status Code: {response.status_code}")
            print(f"Response Content: {response.text}")
            print(f"Response Headers: {dict(response.headers)}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == '__main__':
    test_webhook()