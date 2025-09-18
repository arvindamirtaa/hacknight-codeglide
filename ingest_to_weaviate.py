#!/usr/bin/env python3
"""
Script to ingest GitHub issues dataset from JSONL file into Weaviate.
"""

import json
import os
import sys
from typing import Dict, Any, List
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType


def connect_to_weaviate():
    """Connect to Weaviate Cloud using environment variables."""
    weaviate_url = os.environ.get("WEAVIATE_URL")
    weaviate_api_key = os.environ.get("WEAVIATE_API_KEY")

    if not weaviate_url or not weaviate_api_key:
        print("Error: WEAVIATE_URL and WEAVIATE_API_KEY environment variables must be set")
        sys.exit(1)

    try:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key),
        )

        if not client.is_ready():
            print("Error: Could not connect to Weaviate")
            sys.exit(1)

        print("Successfully connected to Weaviate")
        return client
    except Exception as e:
        print(f"Error connecting to Weaviate: {e}")
        sys.exit(1)


def create_github_issues_collection(client):
    """Create a collection for GitHub issues with appropriate schema."""
    collection_name = "GitHubIssue"

    # Check if collection already exists and delete it to start fresh
    try:
        existing_collection = client.collections.get(collection_name)
        print(f"Collection '{collection_name}' already exists. Deleting to start fresh...")
        client.collections.delete(collection_name)
        print(f"Deleted existing collection '{collection_name}'")
    except Exception:
        # Collection doesn't exist, which is fine
        print(f"Collection '{collection_name}' does not exist yet")

    try:
        # Create collection with explicit schema and text vectorization
        collection = client.collections.create(
            name=collection_name,
            vector_config=Configure.Vectors.text2vec_weaviate(),
            description="GitHub issues and pull requests from the datasets repository",
            properties=[
                Property(name="issue_id", data_type=DataType.INT),
                Property(name="number", data_type=DataType.INT),
                Property(name="title", data_type=DataType.TEXT),
                Property(name="body", data_type=DataType.TEXT),
                Property(name="state", data_type=DataType.TEXT),
                Property(name="url", data_type=DataType.TEXT),
                Property(name="api_url", data_type=DataType.TEXT),
                Property(name="created_at", data_type=DataType.NUMBER),
                Property(name="updated_at", data_type=DataType.NUMBER),
                Property(name="closed_at", data_type=DataType.NUMBER),
                Property(name="is_pull_request", data_type=DataType.BOOL),
                Property(name="author_login", data_type=DataType.TEXT),
                Property(name="author_association", data_type=DataType.TEXT),
                Property(name="comments_text", data_type=DataType.TEXT),
                Property(name="combined_text", data_type=DataType.TEXT),
                Property(name="labels", data_type=DataType.TEXT_ARRAY),
                Property(name="locked", data_type=DataType.BOOL),
                Property(name="assignees", data_type=DataType.TEXT_ARRAY),
            ]
        )

        print(f"Created collection '{collection_name}'")
        return collection
    except Exception as e:
        print(f"Error creating collection: {e}")
        sys.exit(1)


def prepare_issue_data(issue: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare issue data for ingestion into Weaviate."""
    # Combine title and body for better text search
    combined_text = f"{issue.get('title', '')} {issue.get('body', '')}"

    # Prepare comments text
    comments_text = ""
    if issue.get('comments') and isinstance(issue['comments'], list):
        comments_text = " ".join(issue['comments'])

    # Helper function to normalize timestamps to seconds
    def normalize_timestamp(timestamp):
        if timestamp is None:
            return None
        if isinstance(timestamp, (int, float)):
            # Check if timestamp is in milliseconds (greater than year 2100 in seconds)
            if timestamp > 4102444800:  # Jan 1, 2100 in seconds
                timestamp = timestamp / 1000  # Convert milliseconds to seconds
            return timestamp
        return None

    # Extract key fields for structured data
    prepared_data = {
        "issue_id": issue.get("id"),
        "number": issue.get("number"),
        "title": issue.get("title", ""),
        "body": issue.get("body", ""),
        "state": issue.get("state", ""),
        "url": issue.get("html_url", ""),
        "api_url": issue.get("url", ""),
        "created_at": normalize_timestamp(issue.get("created_at")),
        "updated_at": normalize_timestamp(issue.get("updated_at")),
        "closed_at": normalize_timestamp(issue.get("closed_at")),
        "is_pull_request": bool(issue.get("pull_request")),
        "author_login": issue.get("user", {}).get("login", "") if issue.get("user") else "",
        "author_association": issue.get("author_association", ""),
        "comments_text": comments_text,
        "combined_text": combined_text,
        "labels": [label.get("name", "") for label in issue.get("labels", []) if isinstance(label, dict)],
        "locked": issue.get("locked", False),
        "assignees": [assignee.get("login", "") for assignee in issue.get("assignees", []) if isinstance(assignee, dict)]
    }

    return prepared_data


def load_and_ingest_data(client, jsonl_file_path: str):
    """Load JSONL file and ingest data into Weaviate."""
    collection = create_github_issues_collection(client)

    print(f"Loading data from {jsonl_file_path}")

    try:
        with open(jsonl_file_path, 'r', encoding='utf-8') as file:
            issues = []
            line_count = 0

            for line in file:
                line_count += 1
                try:
                    issue = json.loads(line.strip())
                    prepared_issue = prepare_issue_data(issue)
                    issues.append(prepared_issue)

                    # Process in batches of 100
                    if len(issues) >= 100:
                        ingest_batch(collection, issues)
                        issues = []
                        print(f"Processed {line_count} issues...")

                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON on line {line_count}: {e}")
                    continue
                except Exception as e:
                    print(f"Error processing issue on line {line_count}: {e}")
                    continue

            # Process remaining issues
            if issues:
                ingest_batch(collection, issues)

            print(f"Completed ingestion of {line_count} issues")

    except FileNotFoundError:
        print(f"Error: File {jsonl_file_path} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)


def ingest_batch(collection, issues: List[Dict[str, Any]]):
    """Ingest a batch of issues into Weaviate."""
    try:
        with collection.batch.fixed_size(batch_size=100) as batch:
            for issue in issues:
                batch.add_object(issue)
        print(f"Successfully ingested batch of {len(issues)} issues")
    except Exception as e:
        print(f"Error ingesting batch: {e}")
        # Continue with next batch rather than failing completely


def main():
    """Main function to run the ingestion process."""
    jsonl_file = "data/datasets-issues-with-comments.jsonl"

    print("Starting GitHub issues ingestion to Weaviate...")

    # Connect to Weaviate
    client = connect_to_weaviate()

    try:
        # Load and ingest data
        load_and_ingest_data(client, jsonl_file)

        print("Ingestion completed successfully!")

        # Show some stats
        collection = client.collections.get("GitHubIssue")
        total_objects = collection.aggregate.over_all(total_count=True)
        print(f"Total objects in collection: {total_objects.total_count}")

    finally:
        client.close()


if __name__ == "__main__":
    main()