#!/usr/bin/env python3
"""Test for conversations with agents in different pages."""

import requests

def test_pages_for_agents():
    """Test different pages to find conversations with agents."""
    for page in [50, 100, 150]:
        try:
            resp = requests.get(f'http://localhost:8000/api/conversations?page={page}&page_size=10')
            if resp.status_code == 200:
                data = resp.json()
                conversations_with_agents = [c for c in data['conversations'] if c.get('agents')]
                print(f'Page {page}: Found {len(conversations_with_agents)} conversations with agents out of {len(data["conversations"])}')
                
                if conversations_with_agents:
                    conv = conversations_with_agents[0]
                    agent_names = [a["username"] for a in conv["agents"][:3]]
                    print(f'  Sample: {conv["chat_id"]} has {len(conv["agents"])} agents: {agent_names}')
                    return  # Found some, exit
            else:
                print(f'Page {page}: Error {resp.status_code}')
        except Exception as e:
            print(f'Page {page}: Error {e}')
    
    print('No conversations with agents found in tested pages')

if __name__ == "__main__":
    test_pages_for_agents()
