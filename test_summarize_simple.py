#!/usr/bin/env python3
"""
Test summarize endpoint with the issue IDs we can see working
"""

import requests

BASE_URL = "http://localhost:8080"

def test_summarize_demo():
    """Test summarize with the issue IDs that we know exist from debug"""
    print("=== Testing Summarize (Demo Mode) ===")

    # Use the issue IDs we saw in the debug output
    payload = {
        "issue_ids": [763303606, 798879180, 770582960],
        "summary_type": "brief"
    }

    response = requests.post(f"{BASE_URL}/summarize", json=payload)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Total issues: {data['total_issues']}")
        print(f"✅ Open: {data['open_issues']}, Closed: {data['closed_issues']}")
        print(f"✅ Pull requests: {data['pull_requests']}, Issues: {data['issues']}")
        print(f"✅ Common labels: {data['common_labels']}")
        print(f"✅ Authors: {data['authors']}")

        # Test themes
        print("\n=== Testing Themes Summary ===")
        payload["summary_type"] = "themes"
        response = requests.post(f"{BASE_URL}/summarize", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Common themes: {data.get('common_themes', [])[:5]}")
        else:
            print(f"❌ Themes error: {response.text}")
    else:
        print(f"❌ Error: {response.text}")

if __name__ == "__main__":
    test_summarize_demo()