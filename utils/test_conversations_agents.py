#!/usr/bin/env python3
"""Test conversations list with agents."""

import requests

def test_conversations_with_agents():
    """Test conversations list to find one with agents."""
    try:
        resp = requests.get('http://localhost:8000/api/conversations?page=1&page_size=10')
        print(f'Status: {resp.status_code}')
        
        if resp.status_code == 200:
            data = resp.json()
            print(f'Total conversations: {data.get("total", 0)}')
            
            conversations = data.get('conversations', [])
            print(f'\nTesting {len(conversations)} conversations for agent data:')
            
            found_agents = False
            for i, conv in enumerate(conversations):
                agents = conv.get('agents', [])
                if agents:
                    print(f'\n✅ Conversation {i+1}: {conv["chat_id"]}')
                    print(f'  Customer: {conv["username"]}')
                    print(f'  Agents ({len(agents)}):')
                    for agent in agents[:3]:  # Show first 3
                        print(f'    - {agent["username"]} ({agent.get("email", "no email")})')
                    if len(agents) > 3:
                        print(f'    ... and {len(agents) - 3} more')
                    print(f'  Messages: {conv["total_messages"]} total')
                    found_agents = True
                    break
            
            if not found_agents:
                print('❌ No conversations with agents found in first 10 results')
                # Test a specific known multi-agent conversation
                print('\nTesting specific multi-agent conversation...')
                resp2 = requests.get('http://localhost:8000/api/conversations/61751db99b8246ed5141064a')
                if resp2.status_code == 200:
                    conv_data = resp2.json()
                    print(f'✅ Multi-agent conversation: {len(conv_data["agents"])} agents')
                    for agent in conv_data["agents"][:3]:
                        print(f'  - {agent["username"]}')
                        
        else:
            print(f'Error: {resp.text}')
            
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    test_conversations_with_agents()
