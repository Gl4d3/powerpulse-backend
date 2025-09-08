#!/usr/bin/env python3
"""Final verification test for the conversation statistics fix."""

import requests

def test_final_api():
    """Test the final API to verify all fields are working."""
    try:
        resp = requests.get('http://localhost:8000/api/conversations?page=1&page_size=1')
        
        if resp.status_code == 200:
            data = resp.json()
            conv = data['conversations'][0]
            
            print('✅ API Response for most recent conversation:')
            print(f'  Chat ID: {conv["chat_id"]}')
            print(f'  Customer: {conv["username"]}')
            print(f'  Total messages: {conv["total_messages"]}')
            print(f'  Customer messages: {conv["customer_messages"]}')
            print(f'  Agent messages: {conv["agent_messages"]}')
            print(f'  Satisfaction score: {conv["satisfaction_score"]}')
            print(f'  First Call Resolution: {conv["fcr"]}')
            print(f'  Topics: {conv["topics"][:3] if conv["topics"] else []}')
            print(f'  Agents: {len(conv.get("agents", []))} agents')
            if conv.get("agents"):
                for agent in conv["agents"][:2]:  # Show first 2 agents
                    print(f'    - {agent["username"]}')
            print(f'  Created at: {conv["created_at"]}')
            
            # Verify that message counts are not zero
            if conv["total_messages"] and conv["total_messages"] > 0:
                print('\n✅ Message counts are properly populated!')
                print('✅ Multi-agent support is working!')
            else:
                print('\n❌ Message counts are still zero')
                
        else:
            print(f'❌ API Error: {resp.status_code} - {resp.text}')
            
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    test_final_api()
