"""Jira provider using atlassian-python-api for integrations-mcp.

Env vars required:
  JIRA_URL        – Jira Cloud or Server base URL (e.g. https://myco.atlassian.net)
  JIRA_USER       – User email (Cloud) or username (Server)
  JIRA_API_TOKEN  – API token (Cloud) or password (Server)
"""

import os

from mcp.server.fastmcp import FastMCP


def _get_client():
    """Create and return an authenticated Jira client."""
    from atlassian import Jira
    url = os.environ.get("JIRA_URL", "")
    user = os.environ.get("JIRA_USER", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not all([url, user, token]):
        raise RuntimeError(
            "JIRA_URL, JIRA_USER, and JIRA_API_TOKEN environment variables are required"
        )
    return Jira(url=url, username=user, password=token)


def register(mcp: FastMCP) -> None:
    """Register Jira tools with the MCP server."""

    @mcp.tool()
    def jira_list_projects(max_results: int = 50) -> dict:
        """List all Jira projects accessible to the authenticated user.

        Args:
            max_results: Maximum number of projects to return (default 50).

        Returns:
            List of projects with key, name, id, and project type.
        """
        client = _get_client()
        projects = client.projects(included_archived=None)
        results = []
        for p in projects[:max_results]:
            results.append({
                "id": p.get("id", ""),
                "key": p.get("key", ""),
                "name": p.get("name", ""),
                "project_type": p.get("projectTypeKey", ""),
                "style": p.get("style", ""),
            })
        return {"total": len(projects), "projects": results}

    @mcp.tool()
    def jira_list_issues(
        project_key: str,
        status: str = "",
        assignee: str = "",
        max_results: int = 50,
    ) -> dict:
        """List issues in a Jira project using JQL.

        Args:
            project_key: The project key (e.g. "PROJ").
            status: Filter by status name (optional, e.g. "In Progress").
            assignee: Filter by assignee display name or "currentUser()" (optional).
            max_results: Maximum number of issues to return (default 50).

        Returns:
            List of matching issues with key, summary, status, assignee, and priority.
        """
        client = _get_client()
        jql_parts = [f"project = {project_key}"]
        if status:
            jql_parts.append(f"status = '{status}'")
        if assignee:
            if assignee.lower() == "currentuser()":
                jql_parts.append("assignee = currentUser()")
            else:
                jql_parts.append(f"assignee = '{assignee}'")
        jql = " AND ".join(jql_parts) + " ORDER BY created DESC"

        data = client.jql(jql, limit=max_results, fields="summary,status,assignee,priority,issuetype")
        issues = []
        for issue in data.get("issues", []):
            f = issue.get("fields", {})
            a = f.get("assignee")
            issues.append({
                "key": issue["key"],
                "summary": f.get("summary", ""),
                "status": f.get("status", {}).get("name", "") if f.get("status") else "",
                "assignee": a.get("displayName", "") if a else None,
                "priority": f.get("priority", {}).get("name", "") if f.get("priority") else "",
                "issue_type": f.get("issuetype", {}).get("name", "") if f.get("issuetype") else "",
            })
        return {"total": data.get("total", len(issues)), "issues": issues}

    @mcp.tool()
    def jira_get_issue(issue_key: str) -> dict:
        """Get details of a specific Jira issue by its key.

        Args:
            issue_key: The issue key (e.g. "PROJ-123").

        Returns:
            Issue details including summary, status, assignee, description, and more.
        """
        client = _get_client()
        data = client.issue(issue_key)
        fields = data.get("fields", {})
        assignee = fields.get("assignee")
        reporter = fields.get("reporter")
        return {
            "key": data["key"],
            "id": data["id"],
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", ""),
            "issue_type": fields.get("issuetype", {}).get("name", ""),
            "priority": fields.get("priority", {}).get("name", ""),
            "assignee": assignee.get("displayName", "") if assignee else None,
            "reporter": reporter.get("displayName", "") if reporter else None,
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "labels": fields.get("labels", []),
            "description": fields.get("description"),
        }

    @mcp.tool()
    def jira_create_issue(
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: str = "",
        assignee_account_id: str = "",
        priority: str = "",
        labels: list[str] | None = None,
    ) -> dict:
        """Create a new Jira issue.

        Args:
            project_key: The project key (e.g. "PROJ").
            summary: Issue summary/title.
            issue_type: Issue type name (default "Task"). Common values: Task, Bug, Story, Epic.
            description: Plain text description of the issue.
            assignee_account_id: Atlassian account ID of the assignee (optional).
            priority: Priority name (e.g. "High", "Medium", "Low") (optional).
            labels: List of label strings (optional).

        Returns:
            Created issue key, id, and self link.
        """
        client = _get_client()
        fields: dict = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }
        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }
        if assignee_account_id:
            fields["assignee"] = {"accountId": assignee_account_id}
        if priority:
            fields["priority"] = {"name": priority}
        if labels:
            fields["labels"] = labels

        data = client.create_issue(fields=fields)
        return {"key": data["key"], "id": data["id"], "self": data.get("self", "")}

    @mcp.tool()
    def jira_update_issue(
        issue_key: str,
        summary: str = "",
        description: str = "",
        assignee_account_id: str = "",
        priority: str = "",
        labels: list[str] | None = None,
    ) -> dict:
        """Update an existing Jira issue.

        Args:
            issue_key: The issue key (e.g. "PROJ-123").
            summary: New summary (optional, leave empty to keep current).
            description: New plain text description (optional).
            assignee_account_id: New assignee Atlassian account ID (optional).
            priority: New priority name (optional).
            labels: New labels list (optional, replaces existing labels).

        Returns:
            Confirmation of the update.
        """
        client = _get_client()
        fields: dict = {}
        if summary:
            fields["summary"] = summary
        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }
        if assignee_account_id:
            fields["assignee"] = {"accountId": assignee_account_id}
        if priority:
            fields["priority"] = {"name": priority}
        if labels is not None:
            fields["labels"] = labels

        if not fields:
            return {"status": "no_changes", "issue_key": issue_key}

        client.update_issue_field(issue_key, fields)
        return {"status": "updated", "issue_key": issue_key}

    @mcp.tool()
    def jira_add_comment(issue_key: str, body: str) -> dict:
        """Add a comment to a Jira issue.

        Args:
            issue_key: The issue key (e.g. "PROJ-123").
            body: Plain text comment body.

        Returns:
            Created comment ID, author, and timestamp.
        """
        client = _get_client()
        data = client.issue_add_comment(issue_key, body)
        author = data.get("author", {})
        return {
            "id": data.get("id", ""),
            "author": author.get("displayName", ""),
            "created": data.get("created", ""),
            "issue_key": issue_key,
        }

    @mcp.tool()
    def jira_list_sprints(board_id: int, state: str = "active") -> dict:
        """List sprints for a Jira board.

        Args:
            board_id: The Jira board ID (numeric). Use jira_list_projects and the Jira UI to find board IDs.
            state: Filter by sprint state: "active", "future", "closed", or comma-separated combination (default "active").

        Returns:
            List of sprints with id, name, state, and dates.
        """
        client = _get_client()
        # atlassian-python-api doesn't have a direct sprints method on Jira,
        # so we use the underlying request to the Agile API.
        url = f"rest/agile/1.0/board/{board_id}/sprint"
        params = {"state": state}
        data = client.get(url, params=params)
        sprints = []
        for s in data.get("values", []):
            sprints.append({
                "id": s["id"],
                "name": s.get("name", ""),
                "state": s.get("state", ""),
                "start_date": s.get("startDate"),
                "end_date": s.get("endDate"),
                "complete_date": s.get("completeDate"),
                "goal": s.get("goal", ""),
            })
        return {"board_id": board_id, "sprints": sprints}
