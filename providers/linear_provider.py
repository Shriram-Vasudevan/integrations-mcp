"""Linear project-management provider using the Linear GraphQL API."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

LINEAR_API_URL = "https://api.linear.app/graphql"


def _get_api_key() -> str:
    key = os.environ.get("LINEAR_API_KEY")
    if not key:
        raise RuntimeError("LINEAR_API_KEY environment variable is not set")
    return key


async def _graphql(query: str, variables: Optional[dict] = None) -> dict:
    """Execute a GraphQL request against the Linear API."""
    headers = {
        "Authorization": _get_api_key(),
        "Content-Type": "application/json",
    }
    payload: dict = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            LINEAR_API_URL, json=payload, headers=headers, timeout=30.0
        )
        resp.raise_for_status()
        body = resp.json()

    if "errors" in body:
        raise RuntimeError(f"Linear API errors: {body['errors']}")
    return body.get("data", {})


def register(mcp: FastMCP) -> None:
    """Register Linear tools with the MCP server."""

    @mcp.tool()
    async def linear_list_issues(
        team_id: Optional[str] = None,
        status: Optional[str] = None,
        assignee_id: Optional[str] = None,
        first: int = 50,
    ) -> dict:
        """List issues from Linear with optional filters.

        Args:
            team_id: Filter by team ID.
            status: Filter by status name (e.g. "In Progress", "Done").
            assignee_id: Filter by assignee user ID.
            first: Number of issues to return (default 50, max 100).

        Returns:
            List of issues with key details.
        """
        first = max(1, min(first, 100))
        filters = []
        if team_id:
            filters.append('team: { id: { eq: "%s" } }' % team_id)
        if status:
            filters.append('state: { name: { eq: "%s" } }' % status)
        if assignee_id:
            filters.append('assignee: { id: { eq: "%s" } }' % assignee_id)

        filter_clause = ""
        if filters:
            filter_clause = "filter: { %s }" % ", ".join(filters)

        query = """
        query($first: Int!) {
          issues(%s, first: $first) {
            nodes {
              id
              identifier
              title
              priority
              priorityLabel
              state { name }
              assignee { id name }
              team { id name key }
              createdAt
              updatedAt
            }
          }
        }
        """ % filter_clause
        data = await _graphql(query, {"first": first})
        return {"issues": data.get("issues", {}).get("nodes", [])}

    @mcp.tool()
    async def linear_get_issue(issue_id: str) -> dict:
        """Get detailed information about a single Linear issue.

        Args:
            issue_id: The issue ID or identifier (e.g. "ENG-123" or a UUID).

        Returns:
            Full issue details including description, labels, comments, and relations.
        """
        if "-" in issue_id and not all(c in "0123456789abcdef-" for c in issue_id):
            query = """
            query($identifier: String!) {
              issueSearch(filter: { identifier: { eq: $identifier } }, first: 1) {
                nodes {
                  id
                  identifier
                  title
                  description
                  priority
                  priorityLabel
                  estimate
                  state { id name }
                  assignee { id name email }
                  team { id name key }
                  project { id name }
                  cycle { id name number }
                  labels { nodes { id name color } }
                  comments { nodes { id body user { name } createdAt } }
                  createdAt
                  updatedAt
                  url
                }
              }
            }
            """
            data = await _graphql(query, {"identifier": issue_id})
            nodes = data.get("issueSearch", {}).get("nodes", [])
            if nodes:
                return nodes[0]
            raise ValueError(f"Issue not found: {issue_id}")
        else:
            query = """
            query($id: String!) {
              issue(id: $id) {
                id
                identifier
                title
                description
                priority
                priorityLabel
                estimate
                state { id name }
                assignee { id name email }
                team { id name key }
                project { id name }
                cycle { id name number }
                labels { nodes { id name color } }
                comments { nodes { id body user { name } createdAt } }
                createdAt
                updatedAt
                url
              }
            }
            """
            data = await _graphql(query, {"id": issue_id})
            return data.get("issue", {})

    @mcp.tool()
    async def linear_create_issue(
        team_id: str,
        title: str,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        assignee_id: Optional[str] = None,
        state_id: Optional[str] = None,
        project_id: Optional[str] = None,
        cycle_id: Optional[str] = None,
        estimate: Optional[int] = None,
        label_ids: Optional[list[str]] = None,
    ) -> dict:
        """Create a new issue in Linear.

        Args:
            team_id: ID of the team to create the issue in (required).
            title: Issue title (required).
            description: Markdown description of the issue.
            priority: Priority (0=none, 1=urgent, 2=high, 3=medium, 4=low).
            assignee_id: User ID to assign the issue to.
            state_id: Workflow state ID.
            project_id: Project ID to associate with.
            cycle_id: Cycle ID to associate with.
            estimate: Point estimate for the issue.
            label_ids: List of label IDs to apply.

        Returns:
            The created issue with id, identifier, title, and URL.
        """
        query = """
        mutation($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              identifier
              title
              url
              state { name }
              assignee { name }
              team { key }
            }
          }
        }
        """
        input_data: dict = {"teamId": team_id, "title": title}
        if description is not None:
            input_data["description"] = description
        if priority is not None:
            input_data["priority"] = priority
        if assignee_id is not None:
            input_data["assigneeId"] = assignee_id
        if state_id is not None:
            input_data["stateId"] = state_id
        if project_id is not None:
            input_data["projectId"] = project_id
        if cycle_id is not None:
            input_data["cycleId"] = cycle_id
        if estimate is not None:
            input_data["estimate"] = estimate
        if label_ids is not None:
            input_data["labelIds"] = label_ids

        data = await _graphql(query, {"input": input_data})
        result = data.get("issueCreate", {})
        if not result.get("success"):
            raise RuntimeError("Failed to create issue")
        return result.get("issue", {})

    @mcp.tool()
    async def linear_update_issue(
        issue_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[int] = None,
        assignee_id: Optional[str] = None,
        state_id: Optional[str] = None,
        project_id: Optional[str] = None,
        cycle_id: Optional[str] = None,
        estimate: Optional[int] = None,
        label_ids: Optional[list[str]] = None,
    ) -> dict:
        """Update an existing Linear issue.

        Args:
            issue_id: ID of the issue to update (required).
            title: New title.
            description: New markdown description.
            priority: New priority (0=none, 1=urgent, 2=high, 3=medium, 4=low).
            assignee_id: New assignee user ID.
            state_id: New workflow state ID.
            project_id: New project ID.
            cycle_id: New cycle ID.
            estimate: New point estimate.
            label_ids: New list of label IDs.

        Returns:
            The updated issue.
        """
        query = """
        mutation($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
            issue {
              id
              identifier
              title
              url
              state { name }
              assignee { name }
              team { key }
            }
          }
        }
        """
        input_data: dict = {}
        if title is not None:
            input_data["title"] = title
        if description is not None:
            input_data["description"] = description
        if priority is not None:
            input_data["priority"] = priority
        if assignee_id is not None:
            input_data["assigneeId"] = assignee_id
        if state_id is not None:
            input_data["stateId"] = state_id
        if project_id is not None:
            input_data["projectId"] = project_id
        if cycle_id is not None:
            input_data["cycleId"] = cycle_id
        if estimate is not None:
            input_data["estimate"] = estimate
        if label_ids is not None:
            input_data["labelIds"] = label_ids

        if not input_data:
            raise ValueError("At least one field must be provided to update")

        data = await _graphql(query, {"id": issue_id, "input": input_data})
        result = data.get("issueUpdate", {})
        if not result.get("success"):
            raise RuntimeError("Failed to update issue")
        return result.get("issue", {})

    @mcp.tool()
    async def linear_update_issue_status(issue_id: str, state_id: str) -> dict:
        """Update the workflow status of a Linear issue.

        This is a convenience wrapper around linear_update_issue focused on
        status transitions.  Use linear_get_team to discover available workflow
        state IDs for a team.

        Args:
            issue_id: ID of the issue to update (UUID).
            state_id: Target workflow state ID (UUID).

        Returns:
            The updated issue with its new state.
        """
        query = """
        mutation($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
            issue {
              id
              identifier
              title
              url
              state { id name }
              team { key }
            }
          }
        }
        """
        data = await _graphql(query, {"id": issue_id, "input": {"stateId": state_id}})
        result = data.get("issueUpdate", {})
        if not result.get("success"):
            raise RuntimeError("Failed to update issue status")
        return result.get("issue", {})

    @mcp.tool()
    async def linear_list_projects(first: int = 50) -> dict:
        """List projects in the Linear workspace.

        Args:
            first: Number of projects to return (default 50, max 100).

        Returns:
            List of projects with id, name, state, and progress.
        """
        first = max(1, min(first, 100))
        query = """
        query($first: Int!) {
          projects(first: $first) {
            nodes {
              id
              name
              description
              state
              progress
              startDate
              targetDate
              teams { nodes { id name key } }
              lead { id name }
            }
          }
        }
        """
        data = await _graphql(query, {"first": first})
        return {"projects": data.get("projects", {}).get("nodes", [])}

    @mcp.tool()
    async def linear_get_project(project_id: str) -> dict:
        """Get detailed information about a single Linear project.

        Args:
            project_id: The project ID (UUID).

        Returns:
            Full project details including description, status, members, and milestones.
        """
        query = """
        query($id: String!) {
          project(id: $id) {
            id
            name
            description
            state
            progress
            startDate
            targetDate
            lead { id name email }
            members { nodes { id name email } }
            teams { nodes { id name key } }
            issues { nodes { id identifier title state { name } } }
            url
            createdAt
            updatedAt
          }
        }
        """
        data = await _graphql(query, {"id": project_id})
        return data.get("project", {})

    @mcp.tool()
    async def linear_list_teams() -> dict:
        """List all teams in the Linear workspace.

        Returns:
            List of teams with id, name, key, and description.
        """
        query = """
        query {
          teams {
            nodes {
              id
              name
              key
              description
            }
          }
        }
        """
        data = await _graphql(query)
        return {"teams": data.get("teams", {}).get("nodes", [])}

    @mcp.tool()
    async def linear_get_team(team_id: str) -> dict:
        """Get detailed information about a single Linear team.

        Args:
            team_id: The team ID (UUID).

        Returns:
            Full team details including name, key, members, workflow states, and settings.
        """
        query = """
        query($id: String!) {
          team(id: $id) {
            id
            name
            key
            description
            icon
            color
            timezone
            issueEstimationType
            defaultIssueEstimate
            members { nodes { id name email } }
            states { nodes { id name color type position } }
            labels { nodes { id name color } }
            createdAt
            updatedAt
          }
        }
        """
        data = await _graphql(query, {"id": team_id})
        return data.get("team", {})

    @mcp.tool()
    async def linear_list_cycles(team_id: str, first: int = 10) -> dict:
        """List cycles for a specific team.

        Args:
            team_id: The team ID to list cycles for (required).
            first: Number of cycles to return (default 10, max 50).

        Returns:
            List of cycles with id, name, number, dates, and progress.
        """
        first = max(1, min(first, 50))
        query = """
        query($teamId: String!, $first: Int!) {
          team(id: $teamId) {
            cycles(first: $first) {
              nodes {
                id
                name
                number
                startsAt
                endsAt
                completedAt
                progress
                issueCountHistory
                scopeHistory
              }
            }
          }
        }
        """
        data = await _graphql(query, {"teamId": team_id, "first": first})
        return {
            "cycles": data.get("team", {}).get("cycles", {}).get("nodes", [])
        }

    @mcp.tool()
    async def linear_list_labels(team_id: Optional[str] = None, first: int = 50) -> dict:
        """List labels in the Linear workspace, optionally filtered by team.

        Args:
            team_id: Filter labels by team ID (optional). If not provided, returns workspace-level labels.
            first: Number of labels to return (default 50, max 100).

        Returns:
            List of labels with id, name, color, and description.
        """
        first = max(1, min(first, 100))
        if team_id:
            query = """
            query($teamId: String!, $first: Int!) {
              team(id: $teamId) {
                labels(first: $first) {
                  nodes {
                    id
                    name
                    color
                    description
                    parent { id name }
                  }
                }
              }
            }
            """
            data = await _graphql(query, {"teamId": team_id, "first": first})
            return {
                "labels": data.get("team", {}).get("labels", {}).get("nodes", [])
            }
        else:
            query = """
            query($first: Int!) {
              issueLabels(first: $first) {
                nodes {
                  id
                  name
                  color
                  description
                  parent { id name }
                  team { id name key }
                }
              }
            }
            """
            data = await _graphql(query, {"first": first})
            return {
                "labels": data.get("issueLabels", {}).get("nodes", [])
            }

    @mcp.tool()
    async def linear_search_issues(
        query_text: str,
        team_id: Optional[str] = None,
        first: int = 50,
    ) -> dict:
        """Search for Linear issues by text query.

        Args:
            query_text: Text to search for in issue titles and descriptions.
            team_id: Optionally restrict search to a specific team ID.
            first: Number of results to return (default 50, max 100).

        Returns:
            List of matching issues with key details.
        """
        first = max(1, min(first, 100))
        filter_clause = ""
        if team_id:
            filter_clause = ', filter: { team: { id: { eq: "%s" } } }' % team_id

        query = """
        query($first: Int!, $query: String!) {
          issueSearch(query: $query%s, first: $first) {
            nodes {
              id
              identifier
              title
              priority
              priorityLabel
              state { name }
              assignee { id name }
              team { id name key }
              project { id name }
              createdAt
              updatedAt
              url
            }
          }
        }
        """ % filter_clause
        data = await _graphql(query, {"first": first, "query": query_text})
        return {"issues": data.get("issueSearch", {}).get("nodes", [])}

    @mcp.tool()
    async def linear_add_comment(issue_id: str, body: str) -> dict:
        """Add a comment to a Linear issue.

        Args:
            issue_id: The issue ID to comment on (UUID).
            body: The comment body in markdown format.

        Returns:
            The created comment with id, body, user, and timestamp.
        """
        query = """
        mutation($input: CommentCreateInput!) {
          commentCreate(input: $input) {
            success
            comment {
              id
              body
              user { id name }
              createdAt
              url
            }
          }
        }
        """
        data = await _graphql(query, {"input": {"issueId": issue_id, "body": body}})
        result = data.get("commentCreate", {})
        if not result.get("success"):
            raise RuntimeError("Failed to add comment")
        return result.get("comment", {})
