#!/usr/bin/env python3
"""
Test summarize endpoint with real issue IDs
"""

import requests
import json

BASE_URL = "http://localhost:8080"

def get_sample_issue_ids():
    """Get some issue IDs from the similar search to use for summarize test"""
    payload = {
        "issue_text": "dataset loading memory",
        "limit": 5
    }
    response = requests.post(f"{BASE_URL}/similar", json=payload)
    if response.status_code == 200:
        data = response.json()
        issue_ids = [issue['issue_id'] for issue in data['similar_issues'] if issue['issue_id']]
        return issue_ids[:3]  # Take first 3
    return []

def test_summarize_with_real_ids():
    """Test summarize with actual issue IDs"""
    print("=== Getting real issue IDs ===")
    issue_ids = get_sample_issue_ids()
    print(f"Found issue IDs: {issue_ids}")

    if not issue_ids:
        print("No issue IDs found, skipping test")
        return

    print("\n=== Testing Summarize with Real IDs ===")

    # Test brief summary
    payload = {
        "issue_ids": issue_ids,
        "summary_type": "brief"
    }

    response = requests.post(f"{BASE_URL}/summarize", json=payload)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total issues: {data['total_issues']}")
        print(f"Open: {data['open_issues']}, Closed: {data['closed_issues']}")
        print(f"Pull requests: {data['pull_requests']}, Issues: {data['issues']}")
        print(f"Common labels: {data['common_labels']}")
        print(f"Authors: {data['authors']}")
    else:
        print(f"Error: {response.text}")

    # Test themes summary
    print("\n=== Testing Themes Summary ===")
    payload["summary_type"] = "themes"

    response = requests.post(f"{BASE_URL}/summarize", json=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"Common themes: {data.get('common_themes', [])[:5]}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_summarize_with_real_ids()