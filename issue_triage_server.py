#!/usr/bin/env python3
"""
Issue Triage Assistant MCP Server

An MCP server that provides issue triage capabilities using Weaviate vector database.
Endpoints:
- /similar: Find similar issues given a new issue description
- /summarize: Generate LLM-assisted summary for a group of issues
- /priorityHint: Simple ranking by similarity + keywords
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import Filter
import httpx

# MCP imports
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from mcp.types import Tool


# Initialize MCP server
mcp = FastMCP("Issue Triage Assistant")

# Global Weaviate client
weaviate_client = None


def get_weaviate_client():
    """Get or create Weaviate client connection."""
    global weaviate_client

    if weaviate_client is None:
        weaviate_url = os.environ.get("WEAVIATE_URL")
        weaviate_api_key = os.environ.get("WEAVIATE_API_KEY")

        if not weaviate_url or not weaviate_api_key:
            raise ValueError("WEAVIATE_URL and WEAVIATE_API_KEY environment variables must be set")

        weaviate_client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key),
        )

    return weaviate_client


@mcp.tool()
def find_similar_issues(issue_text: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Find similar issues based on text similarity using vector search.

    Args:
        issue_text: The text content of the new issue (title + description)
        limit: Maximum number of similar issues to return (default: 5)

    Returns:
        List of similar issues with their details and similarity scores
    """
    try:
        client = get_weaviate_client()
        collection = client.collections.get("GitHubIssue")

        # Perform vector search
        response = collection.query.near_text(
            query=issue_text,
            limit=limit,
            return_metadata=["score", "distance"]
        )

        results = []
        for obj in response.objects:
            issue_data = {
                "issue_id": obj.properties.get("issue_id"),
                "number": obj.properties.get("number"),
                "title": obj.properties.get("title"),
                "body": obj.properties.get("body", "")[:200] + "..." if len(obj.properties.get("body", "")) > 200 else obj.properties.get("body", ""),
                "state": obj.properties.get("state"),
                "url": obj.properties.get("url"),
                "author_login": obj.properties.get("author_login"),
                "labels": obj.properties.get("labels", []),
                "similarity_score": obj.metadata.score,
                "is_pull_request": obj.properties.get("is_pull_request", False)
            }
            results.append(issue_data)

        return results

    except Exception as e:
        return [{"error": f"Failed to find similar issues: {str(e)}"}]


@mcp.tool()
def summarize_issues(issue_ids: List[int], summary_type: str = "brief") -> Dict[str, Any]:
    """
    Generate an LLM-assisted summary for a group of issues.

    Args:
        issue_ids: List of issue IDs to summarize
        summary_type: Type of summary ("brief", "detailed", "themes")

    Returns:
        Summary information including common themes, status overview, and key insights
    """
    try:
        client = get_weaviate_client()
        collection = client.collections.get("GitHubIssue")

        # Fetch issues by IDs
        issues = []
        for issue_id in issue_ids:
            response = collection.query.fetch_objects(
                where=Filter.by_property("issue_id").equal(issue_id),
                limit=1
            )

            if response.objects:
                obj = response.objects[0]
                issue = {
                    "id": obj.properties.get("issue_id"),
                    "number": obj.properties.get("number"),
                    "title": obj.properties.get("title"),
                    "body": obj.properties.get("body", ""),
                    "state": obj.properties.get("state"),
                    "labels": obj.properties.get("labels", []),
                    "is_pull_request": obj.properties.get("is_pull_request", False),
                    "author_login": obj.properties.get("author_login")
                }
                issues.append(issue)

        if not issues:
            return {"error": "No issues found for the provided IDs"}

        # Generate summary based on type
        summary = {
            "total_issues": len(issues),
            "open_issues": len([i for i in issues if i["state"] == "open"]),
            "closed_issues": len([i for i in issues if i["state"] == "closed"]),
            "pull_requests": len([i for i in issues if i["is_pull_request"]]),
            "issues": len([i for i in issues if not i["is_pull_request"]])
        }

        # Extract common labels and themes
        all_labels = []
        for issue in issues:
            all_labels.extend(issue.get("labels", []))

        label_counts = {}
        for label in all_labels:
            label_counts[label] = label_counts.get(label, 0) + 1

        common_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        summary["common_labels"] = common_labels
        summary["authors"] = list(set(i["author_login"] for i in issues if i["author_login"]))

        if summary_type == "detailed":
            summary["issue_details"] = issues
        elif summary_type == "themes":
            # Extract common keywords from titles
            all_titles = " ".join([i["title"] for i in issues]).lower()
            words = all_titles.split()
            word_counts = {}
            for word in words:
                if len(word) > 3:  # Skip short words
                    word_counts[word] = word_counts.get(word, 0) + 1

            common_themes = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            summary["common_themes"] = common_themes

        return summary

    except Exception as e:
        return {"error": f"Failed to summarize issues: {str(e)}"}


@mcp.tool()
def get_priority_hint(issue_text: str, priority_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Provide priority hints for an issue based on similarity to existing issues and keywords.

    Args:
        issue_text: The text content of the issue (title + description)
        priority_keywords: List of keywords that indicate high priority (optional)

    Returns:
        Priority assessment with score, reasoning, and similar high-priority issues
    """
    try:
        # Default high-priority keywords if none provided
        if priority_keywords is None:
            priority_keywords = [
                "critical", "urgent", "crash", "bug", "error", "broken",
                "security", "vulnerability", "data loss", "performance",
                "regression", "blocker", "production", "outage"
            ]

        # Find similar issues first
        similar_issues = find_similar_issues(issue_text, limit=10)

        if isinstance(similar_issues, list) and len(similar_issues) > 0 and "error" not in similar_issues[0]:
            # Calculate priority score
            priority_score = 0
            reasoning = []

            # Check for priority keywords in issue text
            issue_lower = issue_text.lower()
            found_keywords = []
            for keyword in priority_keywords:
                if keyword in issue_lower:
                    found_keywords.append(keyword)
                    priority_score += 2

            if found_keywords:
                reasoning.append(f"Contains priority keywords: {', '.join(found_keywords)}")

            # Analyze similar issues for priority indicators
            similar_open_count = 0
            similar_high_priority = 0

            for issue in similar_issues:
                if issue.get("state") == "open":
                    similar_open_count += 1

                # Check if similar issue has priority labels
                labels = issue.get("labels", [])
                priority_labels = ["critical", "high priority", "urgent", "bug", "security"]
                if any(label.lower() in priority_labels for label in labels):
                    similar_high_priority += 1
                    priority_score += 1

            if similar_open_count > 3:
                priority_score += 2
                reasoning.append(f"Multiple similar open issues found ({similar_open_count})")

            if similar_high_priority > 0:
                priority_score += similar_high_priority
                reasoning.append(f"Similar issues have priority labels ({similar_high_priority})")

            # Determine priority level
            if priority_score >= 8:
                priority_level = "Critical"
            elif priority_score >= 5:
                priority_level = "High"
            elif priority_score >= 2:
                priority_level = "Medium"
            else:
                priority_level = "Low"

            return {
                "priority_level": priority_level,
                "priority_score": priority_score,
                "reasoning": reasoning,
                "similar_issues_count": len(similar_issues),
                "similar_open_issues": similar_open_count,
                "found_keywords": found_keywords,
                "top_similar_issues": similar_issues[:3]
            }
        else:
            # Fallback to keyword-only analysis
            priority_score = 0
            found_keywords = []
            issue_lower = issue_text.lower()

            for keyword in priority_keywords:
                if keyword in issue_lower:
                    found_keywords.append(keyword)
                    priority_score += 2

            priority_level = "High" if priority_score >= 4 else "Medium" if priority_score >= 2 else "Low"

            return {
                "priority_level": priority_level,
                "priority_score": priority_score,
                "reasoning": [f"Based on keywords: {', '.join(found_keywords)}"] if found_keywords else ["No priority indicators found"],
                "found_keywords": found_keywords,
                "note": "Analysis based on keywords only - vector search unavailable"
            }

    except Exception as e:
        return {"error": f"Failed to calculate priority hint: {str(e)}"}


@mcp.tool()
def search_issues_by_label(label: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for issues by label.

    Args:
        label: The label to search for
        limit: Maximum number of issues to return

    Returns:
        List of issues with the specified label
    """
    try:
        client = get_weaviate_client()
        collection = client.collections.get("GitHubIssue")

        response = collection.query.fetch_objects(
            where=Filter.by_property("labels").contains_any([label]),
            limit=limit
        )

        results = []
        for obj in response.objects:
            issue_data = {
                "issue_id": obj.properties.get("issue_id"),
                "number": obj.properties.get("number"),
                "title": obj.properties.get("title"),
                "state": obj.properties.get("state"),
                "url": obj.properties.get("url"),
                "labels": obj.properties.get("labels", []),
                "author_login": obj.properties.get("author_login"),
                "is_pull_request": obj.properties.get("is_pull_request", False)
            }
            results.append(issue_data)

        return results

    except Exception as e:
        return [{"error": f"Failed to search issues by label: {str(e)}"}]


if __name__ == "__main__":
    # Run the MCP server
    import mcp.server.stdio

    async def main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await mcp.run(read_stream, write_stream, mcp.create_initialization_options())

    asyncio.run(main())