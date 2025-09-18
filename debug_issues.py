#!/usr/bin/env python3
"""
Debug issue IDs and see what's in the database
"""

import requests
import json

BASE_URL = "http://localhost:8080"

def debug_similar_search():
    """Debug what the similar search actually returns"""
    payload = {
        "issue_text": "dataset",
        "limit": 3
    }
    response = requests.post(f"{BASE_URL}/similar", json=payload)
    if response.status_code == 200:
        data = response.json()
        print("=== Similar Search Results ===")
        for issue in data['similar_issues']:
            print(f"Issue ID: {issue['issue_id']} (type: {type(issue['issue_id'])})")
            print(f"Number: {issue['number']}")
            print(f"Title: {issue['title']}")
            print("---")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    debug_similar_search()