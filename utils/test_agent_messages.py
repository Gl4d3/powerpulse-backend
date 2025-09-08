#!/usr/bin/env python3
"""Test: fetch messages for a conversation and print agent messages with agent_info."""
import requests
import sys

BASE = 'http://localhost:8000/api'

# Known multi-agent conversation from earlier tests
CHAT_ID = '61751db99b8246ed5141064a'

try:
    resp = requests.get(f"{BASE}/conversations/{CHAT_ID}/messages")
    print('Status:', resp.status_code)
    if resp.status_code != 200:
        print('Response:', resp.text)
        sys.exit(1)
    msgs = resp.json()
    agent_msgs = [m for m in msgs if m.get('direction') == 'to_client']
    print(f'Total messages: {len(msgs)}, Agent messages: {len(agent_msgs)}\n')
    for i, m in enumerate(agent_msgs[:25], 1):
        print(f'{i}. timestamp: {m.get("timestamp")}, content: {m.get("content")[:120]!r}')
        # agent_info may not be present in MessageResponse; try to fetch raw from messages route if available
        # show sentiment/topics if present
        print(f'   sentiment: {m.get("sentiment_score")}, topics: {m.get("topics")}')

except Exception as e:
    print('Error:', e)
    sys.exit(2)
