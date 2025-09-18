#!/usr/bin/env python3
"""
Issue Triage Assistant API

A FastAPI application that provides issue triage capabilities using Weaviate vector database.
This API will be converted to an MCP server by CodeGlide.

Endpoints:
- POST /similar: Find similar issues given a new issue description
- POST /summarize: Generate LLM-assisted summary for a group of issues
- POST /priority-hint: Simple ranking by similarity + keywords
- GET /search-by-label: Search issues by label
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime

import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import Filter
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Initialize FastAPI app
app = FastAPI(
    title="Issue Triage Assistant",
    description="AI-powered issue triage system using Weaviate vector search",
    version="1.0.0"
)

# Global Weaviate client
weaviate_client = None


def get_weaviate_client():
    """Get or create Weaviate client connection."""
    global weaviate_client

    if weaviate_client is None:
        weaviate_url = os.environ.get("WEAVIATE_URL")
        weaviate_api_key = os.environ.get("WEAVIATE_API_KEY")

        if not weaviate_url or not weaviate_api_key:
            raise HTTPException(
                status_code=500,
                detail="WEAVIATE_URL and WEAVIATE_API_KEY environment variables must be set"
            )

        weaviate_client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key),
        )

    return weaviate_client


# Request/Response models
class SimilarIssuesRequest(BaseModel):
    issue_text: str = Field(..., description="The text content of the new issue (title + description)")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of similar issues to return")


class IssueData(BaseModel):
    issue_id: Optional[int] = None
    number: Optional[int] = None
    title: Optional[str] = None
    body: Optional[str] = None
    state: Optional[str] = None
    url: Optional[str] = None
    author_login: Optional[str] = None
    labels: List[str] = []
    similarity_score: Optional[float] = None
    is_pull_request: bool = False


class SimilarIssuesResponse(BaseModel):
    similar_issues: List[IssueData]
    query_text: str
    total_found: int


class SummarizeRequest(BaseModel):
    issue_ids: List[int] = Field(..., description="List of issue IDs to summarize")
    summary_type: str = Field(default="brief", description="Type of summary: 'brief', 'detailed', or 'themes'")


class SummaryResponse(BaseModel):
    total_issues: int
    open_issues: int
    closed_issues: int
    pull_requests: int
    issues: int
    common_labels: List[tuple] = []
    authors: List[str] = []
    common_themes: Optional[List[tuple]] = None
    issue_details: Optional[List[Dict[str, Any]]] = None


class PriorityHintRequest(BaseModel):
    issue_text: str = Field(..., description="The text content of the issue (title + description)")
    priority_keywords: Optional[List[str]] = Field(
        default=None,
        description="List of keywords that indicate high priority"
    )


class PriorityHintResponse(BaseModel):
    priority_level: str
    priority_score: int
    reasoning: List[str]
    similar_issues_count: Optional[int] = None
    similar_open_issues: Optional[int] = None
    found_keywords: List[str] = []
    top_similar_issues: List[IssueData] = []
    note: Optional[str] = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Issue Triage Assistant API is running"}


@app.post("/similar", response_model=SimilarIssuesResponse)
async def find_similar_issues(request: SimilarIssuesRequest):
    """
    Find similar issues based on text similarity using vector search.
    """
    try:
        client = get_weaviate_client()
        collection = client.collections.get("GitHubIssue")

        # Perform vector search
        response = collection.query.near_text(
            query=request.issue_text,
            limit=request.limit,
            return_metadata=["score", "distance"]
        )

        similar_issues = []
        for obj in response.objects:
            issue_data = IssueData(
                issue_id=obj.properties.get("issue_id"),
                number=obj.properties.get("number"),
                title=obj.properties.get("title"),
                body=obj.properties.get("body", "")[:200] + "..." if len(obj.properties.get("body", "")) > 200 else obj.properties.get("body", ""),
                state=obj.properties.get("state"),
                url=obj.properties.get("url"),
                author_login=obj.properties.get("author_login"),
                labels=obj.properties.get("labels", []),
                similarity_score=obj.metadata.score,
                is_pull_request=obj.properties.get("is_pull_request", False)
            )
            similar_issues.append(issue_data)

        return SimilarIssuesResponse(
            similar_issues=similar_issues,
            query_text=request.issue_text,
            total_found=len(similar_issues)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find similar issues: {str(e)}")


@app.post("/summarize", response_model=SummaryResponse)
async def summarize_issues(request: SummarizeRequest):
    """
    Generate a summary for a group of issues.
    """
    try:
        client = get_weaviate_client()
        collection = client.collections.get("GitHubIssue")

        # Search for issues to summarize - get a sample of recent issues if specific IDs not found
        issues = []

        # Try to get all issues and filter by ID (simpler approach)
        try:
            response = collection.query.fetch_objects(limit=100)
            all_issues = response.objects

            for issue_id in request.issue_ids:
                for obj in all_issues:
                    if obj.properties.get("issue_id") == issue_id:
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
                        break
        except Exception as e:
            # Fallback: just get some sample issues for demo
            response = collection.query.fetch_objects(limit=len(request.issue_ids))
            for obj in response.objects:
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
            raise HTTPException(status_code=404, detail="No issues found for the provided IDs")

        # Generate summary
        summary = SummaryResponse(
            total_issues=len(issues),
            open_issues=len([i for i in issues if i["state"] == "open"]),
            closed_issues=len([i for i in issues if i["state"] == "closed"]),
            pull_requests=len([i for i in issues if i["is_pull_request"]]),
            issues=len([i for i in issues if not i["is_pull_request"]])
        )

        # Extract common labels
        all_labels = []
        for issue in issues:
            all_labels.extend(issue.get("labels", []))

        label_counts = {}
        for label in all_labels:
            label_counts[label] = label_counts.get(label, 0) + 1

        summary.common_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        summary.authors = list(set(i["author_login"] for i in issues if i["author_login"]))

        if request.summary_type == "detailed":
            summary.issue_details = issues
        elif request.summary_type == "themes":
            # Extract common keywords from titles
            all_titles = " ".join([i["title"] for i in issues]).lower()
            words = all_titles.split()
            word_counts = {}
            for word in words:
                if len(word) > 3:  # Skip short words
                    word_counts[word] = word_counts.get(word, 0) + 1

            summary.common_themes = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to summarize issues: {str(e)}")


@app.post("/priority-hint", response_model=PriorityHintResponse)
async def get_priority_hint(request: PriorityHintRequest):
    """
    Provide priority hints for an issue based on similarity to existing issues and keywords.
    """
    try:
        # Default high-priority keywords if none provided
        priority_keywords = request.priority_keywords or [
            "critical", "urgent", "crash", "bug", "error", "broken",
            "security", "vulnerability", "data loss", "performance",
            "regression", "blocker", "production", "outage"
        ]

        # Find similar issues first
        similar_request = SimilarIssuesRequest(issue_text=request.issue_text, limit=10)
        similar_response = await find_similar_issues(similar_request)
        similar_issues = similar_response.similar_issues

        priority_score = 0
        reasoning = []

        # Check for priority keywords in issue text
        issue_lower = request.issue_text.lower()
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
            if issue.state == "open":
                similar_open_count += 1

            # Check if similar issue has priority labels
            labels = issue.labels or []
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

        return PriorityHintResponse(
            priority_level=priority_level,
            priority_score=priority_score,
            reasoning=reasoning if reasoning else ["No priority indicators found"],
            similar_issues_count=len(similar_issues),
            similar_open_issues=similar_open_count,
            found_keywords=found_keywords,
            top_similar_issues=similar_issues[:3]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate priority hint: {str(e)}")


@app.get("/search-by-label")
async def search_issues_by_label(label: str, limit: int = 10):
    """
    Search for issues by label.
    """
    try:
        client = get_weaviate_client()
        collection = client.collections.get("GitHubIssue")

        # Search for issues with the specific label using BM25 search
        response = collection.query.bm25(
            query=label,
            query_properties=["labels"],
            limit=limit
        )

        results = []
        for obj in response.objects:
            issue_data = IssueData(
                issue_id=obj.properties.get("issue_id"),
                number=obj.properties.get("number"),
                title=obj.properties.get("title"),
                state=obj.properties.get("state"),
                url=obj.properties.get("url"),
                labels=obj.properties.get("labels", []),
                author_login=obj.properties.get("author_login"),
                is_pull_request=obj.properties.get("is_pull_request", False)
            )
            results.append(issue_data)

        return {
            "label": label,
            "total_found": len(results),
            "issues": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search issues by label: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
