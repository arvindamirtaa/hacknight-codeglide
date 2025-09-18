"""
MCP Server - Python Implementation
"""

import os
import json
import requests
from pathlib import Path
from typing import Annotated
from pydantic import Field
from mcp.server.fastmcp import FastMCP

# Create MCP server instance
mcp = FastMCP("MCP Server")

def get_config():
    """Get configuration from environment or config file."""
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

# Add configuration resource
@mcp.resource("config://settings")
def get_config_resource() -> str:
    """Get current configuration settings."""
    config = get_config()
    return json.dumps({
        "base_url": config.base_url,
        "bearer_token": "***" if config.bearer_token else None
    }, indent=2)

# Tool functions
from registry import (
    find_similar_issues_api,
    get_priority_hint_api,
    summarize_issues_api,
    search_issues_by_label_api,
    health_check_api
)

@mcp.tool()
def find_similar_issues(issue_text: str, limit: int = 5) -> str:
    """
    Find similar issues based on text similarity using vector search.

    Args:
        issue_text: The text content of the new issue (title + description)
        limit: Maximum number of similar issues to return (default: 5, max: 20)

    Returns:
        JSON string with similar issues and their details
    """
    return find_similar_issues_api(issue_text, min(limit, 20))

@mcp.tool()
def get_priority_hint(issue_text: str, priority_keywords: list = None) -> str:
    """
    Get priority assessment for an issue based on content and patterns.

    Args:
        issue_text: The text content of the issue (title + description)
        priority_keywords: Optional list of keywords that indicate high priority

    Returns:
        JSON string with priority assessment and reasoning
    """
    return get_priority_hint_api(issue_text, priority_keywords)

@mcp.tool()
def summarize_issues(issue_ids: list, summary_type: str = "brief") -> str:
    """
    Generate a summary for a group of issues.

    Args:
        issue_ids: List of issue IDs to summarize
        summary_type: Type of summary - "brief", "detailed", or "themes"

    Returns:
        JSON string with summary statistics and insights
    """
    return summarize_issues_api(issue_ids, summary_type)

@mcp.tool()
def search_issues_by_label(label: str, limit: int = 10) -> str:
    """
    Search for issues by label.

    Args:
        label: The label to search for
        limit: Maximum number of issues to return (default: 10)

    Returns:
        JSON string with matching issues
    """
    return search_issues_by_label_api(label, limit)

@mcp.tool()
def api_health_check() -> str:
    """
    Check if the Issue Triage API is running and accessible.

    Returns:
        Status message about API availability
    """
    return health_check_api()

if __name__ == "__main__":
    mcp.run()
