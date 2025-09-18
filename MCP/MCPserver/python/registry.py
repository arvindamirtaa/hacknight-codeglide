"""
MCP tool for No description available
"""

import json
import requests
from typing import Dict, Any, Optional


def find_similar_issues_api(issue_text: str, limit: int = 5) -> str:
    """Find similar issues using the API."""
    try:
        config = get_config()
        if not config.base_url:
            return "Error: Missing API_BASE_URL environment variable."

        payload = {
            "issue_text": issue_text,
            "limit": limit
        }

        url = f"{config.base_url}/similar"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return json.dumps(response.json(), indent=2)
        else:
            return f"API error: {response.status_code} - {response.text}"

    except Exception as e:
        return f"Error: {str(e)}"

def get_priority_hint_api(issue_text: str, priority_keywords: list = None) -> str:
    """Get priority hint using the API."""
    try:
        config = get_config()
        if not config.base_url:
            return "Error: Missing API_BASE_URL environment variable."

        payload = {"issue_text": issue_text}
        if priority_keywords:
            payload["priority_keywords"] = priority_keywords

        url = f"{config.base_url}/priority-hint"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return json.dumps(response.json(), indent=2)
        else:
            return f"API error: {response.status_code} - {response.text}"

    except Exception as e:
        return f"Error: {str(e)}"

def summarize_issues_api(issue_ids: list, summary_type: str = "brief") -> str:
    """Summarize issues using the API."""
    try:
        config = get_config()
        if not config.base_url:
            return "Error: Missing API_BASE_URL environment variable."

        payload = {
            "issue_ids": issue_ids,
            "summary_type": summary_type
        }

        url = f"{config.base_url}/summarize"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return json.dumps(response.json(), indent=2)
        else:
            return f"API error: {response.status_code} - {response.text}"

    except Exception as e:
        return f"Error: {str(e)}"

def search_issues_by_label_api(label: str, limit: int = 10) -> str:
    """Search issues by label using the API."""
    try:
        config = get_config()
        if not config.base_url:
            return "Error: Missing API_BASE_URL environment variable."

        params = {"label": label, "limit": limit}
        url = f"{config.base_url}/search-by-label"
        headers = {"Accept": "application/json"}

        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            return json.dumps(response.json(), indent=2)
        else:
            return f"API error: {response.status_code} - {response.text}"

    except Exception as e:
        return f"Error: {str(e)}"

def health_check_api() -> str:
    """Check API health."""
    try:
        config = get_config()
        if not config.base_url:
            return "Error: Missing API_BASE_URL environment variable."

        url = f"{config.base_url}/"
        headers = {"Accept": "application/json"}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return f"✅ API is healthy: {data.get('message', 'OK')}"
        else:
            return f"⚠️ API responded with status {response.status_code}"

    except Exception as e:
        return f"❌ API is not accessible: {str(e)}"


def get_config():
    """Get configuration from environment or config file."""
    import os
    from pathlib import Path
    
    class Config:
        def __init__(self):
            self.base_url = os.getenv("API_BASE_URL")
            self.bearer_token = os.getenv("API_BEARER_TOKEN")
            
            # Try to load from config file if env vars not set
            if not self.base_url or not self.bearer_token:
                config_path = Path.home() / ".api" / "config.json"
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config_data = json.load(f)
                        self.base_url = self.base_url or config_data.get("baseURL")
                        self.bearer_token = self.bearer_token or config_data.get("bearerToken")
    
    return Config()
