#!/usr/bin/env python3
"""
Test script for the Issue Triage Assistant API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8080"

def test_health_check():
    """Test the root health check endpoint"""
    print("=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_similar_issues():
    """Test the /similar endpoint"""
    print("=== Testing Similar Issues ===")

    # Sample issue text
    issue_text = "The dataset loading function crashes with memory error when processing large CSV files"

    payload = {
        "issue_text": issue_text,
        "limit": 3
    }

    response = requests.post(f"{BASE_URL}/similar", json=payload)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Query: {data['query_text']}")
        print(f"Total found: {data['total_found']}")
        print("Similar issues:")
        for i, issue in enumerate(data['similar_issues'], 1):
            print(f"  {i}. #{issue['number']}: {issue['title']}")
            print(f"     Similarity: {issue['similarity_score']:.4f}")
            print(f"     State: {issue['state']}")
            print(f"     Labels: {issue['labels']}")
    else:
        print(f"Error: {response.text}")
    print()

def test_summarize():
    """Test the /summarize endpoint"""
    print("=== Testing Summarize ===")

    # Use some sample issue IDs (these might not exist)
    payload = {
        "issue_ids": [1003999469, 1003904803, 1002704096],
        "summary_type": "brief"
    }

    response = requests.post(f"{BASE_URL}/summarize", json=payload)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total issues: {data['total_issues']}")
        print(f"Open: {data['open_issues']}, Closed: {data['closed_issues']}")
        print(f"Pull requests: {data['pull_requests']}, Issues: {data['issues']}")
        print(f"Common labels: {data['common_labels'][:3]}")
        print(f"Authors: {data['authors'][:5]}")
    else:
        print(f"Error: {response.text}")
    print()

def test_priority_hint():
    """Test the /priority-hint endpoint"""
    print("=== Testing Priority Hint ===")

    # Sample critical issue
    issue_text = "URGENT: Critical security vulnerability in authentication system causing data loss"

    payload = {
        "issue_text": issue_text
    }

    response = requests.post(f"{BASE_URL}/priority-hint", json=payload)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Priority Level: {data['priority_level']}")
        print(f"Priority Score: {data['priority_score']}")
        print(f"Found Keywords: {data['found_keywords']}")
        print(f"Reasoning: {data['reasoning']}")
        print(f"Similar issues count: {data['similar_issues_count']}")
    else:
        print(f"Error: {response.text}")
    print()

def test_search_by_label():
    """Test the /search-by-label endpoint"""
    print("=== Testing Search by Label ===")

    # Search for enhancement labeled issues
    response = requests.get(f"{BASE_URL}/search-by-label?label=enhancement&limit=3")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Label: {data['label']}")
        print(f"Total found: {data['total_found']}")
        print("Issues:")
        for i, issue in enumerate(data['issues'], 1):
            print(f"  {i}. #{issue['number']}: {issue['title']}")
            print(f"     State: {issue['state']}")
            print(f"     Author: {issue['author_login']}")
    else:
        print(f"Error: {response.text}")
    print()

def test_low_priority_issue():
    """Test priority hint with a low priority issue"""
    print("=== Testing Low Priority Issue ===")

    issue_text = "Update documentation for the new API endpoint"

    payload = {
        "issue_text": issue_text
    }

    response = requests.post(f"{BASE_URL}/priority-hint", json=payload)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Priority Level: {data['priority_level']}")
        print(f"Priority Score: {data['priority_score']}")
        print(f"Reasoning: {data['reasoning']}")
    else:
        print(f"Error: {response.text}")
    print()

if __name__ == "__main__":
    print("Testing Issue Triage Assistant API\n")

    try:
        test_health_check()
        test_similar_issues()
        test_summarize()
        test_priority_hint()
        test_search_by_label()
        test_low_priority_issue()

        print("=== All tests completed ===")

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server.")
        print("Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"Unexpected error: {e}")