#!/usr/bin/env python3
"""Test script to verify the API is working with updated data."""

import requests
import json

def test_conversations_api():
    """Test the conversations API endpoint."""
    try:
        resp = requests.get('http://localhost:8000/api/conversations?limit=5')
        print(f'Status: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            print(f'Total conversations: {data.get("total", 0)}')
            
            conversations = data.get('conversations', [])
            if conversations:
                print('\nSample conversation:')
                conv = conversations[0]
                print(f'  ID: {conv.get("chat_id")}')
                print(f'  Username: {conv.get("username")}')
                print(f'  Total messages: {conv.get("total_messages")}')
                print(f'  Customer messages: {conv.get("customer_messages")}')
                print(f'  Agent messages: {conv.get("agent_messages")}')
                print(f'  First message: {conv.get("first_message_time")}')
                print(f'  Last message: {conv.get("last_message_time")}')
                print(f'  Satisfaction score: {conv.get("satisfaction_score")}')
                print(f'  FCR: {conv.get("fcr")}')
            else:
                print('No conversations returned')
        else:
            print(f'Error: {resp.text}')
            
    except requests.exceptions.ConnectionError:
        print('Server not running - start with: python main.py')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    test_conversations_api()
