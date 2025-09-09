"""
Test script for WebSocket connections
"""
import asyncio
import websockets
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket server URL
WS_URL = 'ws://localhost:8000/ws/'

# Test JWT token (replace with a valid token from your application)
TEST_TOKEN = 'your_test_jwt_token_here'

async def test_admin_websocket():
    """Test admin WebSocket connection"""
    url = f"{WS_URL}admin/activity/?token={TEST_TOKEN}"
    
    try:
        async with websockets.connect(url) as websocket:
            logger.info("Connected to admin WebSocket")
            
            # Send a test message
            message = {
                'type': 'test',
                'data': 'Test message from admin'
            }
            await websocket.send(json.dumps(message))
            logger.info(f"Sent: {message}")
            
            # Wait for response
            response = await websocket.recv()
            logger.info(f"Received: {response}")
            
    except Exception as e:
        logger.error(f"Error in admin WebSocket test: {str(e)}")

async def test_vendor_websocket():
    """Test vendor WebSocket connection"""
    url = f"{WS_URL}vendor/notifications/?token={TEST_TOKEN}"
    
    try:
        async with websockets.connect(url) as websocket:
            logger.info("Connected to vendor WebSocket")
            
            # Send a test message
            message = {
                'type': 'test',
                'data': 'Test message from vendor'
            }
            await websocket.send(json.dumps(message))
            logger.info(f"Sent: {message}")
            
            # Wait for response
            response = await websocket.recv()
            logger.info(f"Received: {response}")
            
    except Exception as e:
        logger.error(f"Error in vendor WebSocket test: {str(e)}")

if __name__ == "__main__":
    # Run the tests
    asyncio.get_event_loop().run_until_complete(test_admin_websocket())
    asyncio.get_event_loop().run_until_complete(test_vendor_websocket())
