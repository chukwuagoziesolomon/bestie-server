"""
Test script for WebSocket server.

This script can be used to test the WebSocket server without a frontend.
"""
import asyncio
import json
import websockets
import argparse
from urllib.parse import urljoin

async def test_admin_websocket(base_url, token):
    """Test admin WebSocket connection."""
    ws_url = urljoin(base_url.replace('http', 'ws'), 'ws/admin/activity/')
    print(f"Connecting to {ws_url}...")
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    async with websockets.connect(ws_url, extra_headers=headers) as websocket:
        print("Connected to admin WebSocket")
        
        # Wait for the connection message
        response = await websocket.recv()
        print(f"Received: {response}")
        
        # Keep the connection open and print any incoming messages
        try:
            while True:
                message = await websocket.recv()
                print(f"Received message: {message}")
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")

async def test_vendor_websocket(base_url, token):
    """Test vendor WebSocket connection."""
    ws_url = urljoin(base_url.replace('http', 'ws'), 'ws/vendor/notifications/')
    print(f"Connecting to {ws_url}...")
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    async with websockets.connect(ws_url, extra_headers=headers) as websocket:
        print("Connected to vendor WebSocket")
        
        # Wait for the connection message
        response = await websocket.recv()
        print(f"Received: {response}")
        
        # Keep the connection open and print any incoming messages
        try:
            while True:
                message = await websocket.recv()
                print(f"Received message: {message}")
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test WebSocket server')
    parser.add_argument('--base-url', type=str, default='http://localhost:8000',
                       help='Base URL of the server (default: http://localhost:8000)')
    parser.add_argument('--token', type=str, required=True,
                       help='JWT token for authentication')
    parser.add_argument('--type', type=str, choices=['admin', 'vendor'], default='vendor',
                       help='Type of WebSocket to test (admin or vendor)')
    
    args = parser.parse_args()
    
    if args.type == 'admin':
        asyncio.get_event_loop().run_until_complete(
            test_admin_websocket(args.base_url, args.token)
        )
    else:
        asyncio.get_event_loop().run_until_complete(
            test_vendor_websocket(args.base_url, args.token)
        )
