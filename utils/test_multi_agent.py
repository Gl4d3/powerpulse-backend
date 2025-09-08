#!/usr/bin/env python3
"""Test multi-agent conversation endpoint."""

import requests

def test_multi_agent_conversation():
    """Test conversation with multiple agents."""
    try:
        # Test known multi-agent conversation
        resp = requests.get('http://localhost:8000/api/conversations/61751db99b8246ed5141064a')
        print(f'Status: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            print(f'Chat ID: {data["chat_id"]}')
            print(f'Customer: {data["username"]}')
            print(f'Message counts: {data["total_messages"]} total, {data["customer_messages"]} customer, {data["agent_messages"]} agent')
            print(f'Agents ({len(data["agents"])}):')
            for agent in data["agents"]:
                email = agent.get("email", "no email")
                print(f'  - {agent["username"]} ({email})')
            print(f'Topics: {data["topics"][:5]}')
            print(f'CSI Score: {data["satisfaction_score"]:.1f}')
            print(f'FCR: {data["fcr"]}')
        else:
            print(f'Error: {resp.text}')
            
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    test_multi_agent_conversation()
