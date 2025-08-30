import asyncio
import websockets
import json
import time

async def test_websocket():
    uri = "ws://localhost:8000/ws/chat/test_user_123/"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        
        # Send initial message
        await websocket.send(json.dumps({
            "type": "chat_message",
            "message": "Hello, WebSocket!"
        }))
        print("Sent initial message")
        
        # Keep connection alive and listen for messages
        try:
            while True:
                try:
                    # Send ping every 15 seconds
                    await asyncio.sleep(15)
                    await websocket.ping()
                    print("Sent ping")
                    
                    # Wait for pong with timeout
                    pong_waiter = await websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10)
                    print("Received pong")
                    
                except asyncio.TimeoutError:
                    print("Ping timeout, reconnecting...")
                    break
                    
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"Connection closed: {e}")
                    break
                    
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await websocket.close()

if __name__ == "__main__":
    while True:
        try:
            asyncio.get_event_loop().run_until_complete(test_websocket())
        except Exception as e:
            print(f"Error in main loop: {e}")
        print("Reconnecting in 5 seconds...")
        time.sleep(5)
