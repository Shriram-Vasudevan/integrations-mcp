"""Asana provider wrapping the Asana REST API v1."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

ASANA_BASE_URL = "https://app.asana.com/api/1.0"


def _get_token() -> str:
    """Return the Asana personal access token from env."""
    token = os.environ.get("ASANA_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("ASANA_ACCESS_TOKEN environment variable is required")
    return token


async def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the Asana REST API v1."""
    token = _get_token()
    url = f"{ASANA_BASE_URL}/{path.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method, url, headers=headers, timeout=30.0, **kwargs
        )
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Asana tools with the MCP server."""

    @mcp.tool()
    async def asana_list_workspaces() -> dict:
        """List all Asana workspaces accessible to the authenticated user.

        Returns:
            List of workspaces with gid, name, and is_organization flag.
        """
        data = await _request("GET", "workspaces")
        workspaces = []
        for w in data.get("data", []):
            workspaces.append({
                "gid": w["gid"],
                "name": w.get("name", ""),
                "is_organization": w.get("is_organization", False),
            })
        return {"workspaces": workspaces}

    @mcp.tool()
    async def asana_list_projects(workspace_gid: str, archived: bool = False) -> dict:
        """List projects in an Asana workspace.

        Args:
            workspace_gid: The workspace GID to list projects from.
            archived: Whether to include archived projects (default false).

        Returns:
            List of projects with gid, name, and color.
        """
        params = {
            "workspace": workspace_gid,
            "archived": str(archived).lower(),
            "opt_fields": "name,color,archived,created_at,modified_at,owner.name",
        }
        data = await _request("GET", "projects", params=params)
        projects = []
        for p in data.get("data", []):
            owner = p.get("owner")
            projects.append({
                "gid": p["gid"],
                "name": p.get("name", ""),
                "color": p.get("color"),
                "archived": p.get("archived", False),
                "created_at": p.get("created_at"),
                "modified_at": p.get("modified_at"),
                "owner": owner.get("name", "") if owner else None,
            })
        return {"workspace_gid": workspace_gid, "projects": projects}

    @mcp.tool()
    async def asana_get_project(project_gid: str) -> dict:
        """Get detailed information about a specific Asana project.

        Args:
            project_gid: The project GID.

        Returns:
            Project details including name, notes, owner, status, and dates.
        """
        params = {
            "opt_fields": "name,notes,color,archived,created_at,modified_at,"
            "due_on,start_on,owner.name,current_status_update.title,"
            "current_status_update.status_type,members.name,workspace.name",
        }
        data = await _request("GET", f"projects/{project_gid}", params=params)
        p = data.get("data", {})
        owner = p.get("owner")
        status = p.get("current_status_update")
        members = [
            {"gid": m["gid"], "name": m.get("name", "")}
            for m in p.get("members", [])
        ]
        return {
            "gid": p.get("gid", project_gid),
            "name": p.get("name", ""),
            "notes": p.get("notes", ""),
            "color": p.get("color"),
            "archived": p.get("archived", False),
            "due_on": p.get("due_on"),
            "start_on": p.get("start_on"),
            "created_at": p.get("created_at"),
            "modified_at": p.get("modified_at"),
            "owner": owner.get("name", "") if owner else None,
            "status": {
                "title": status.get("title", ""),
                "status_type": status.get("status_type", ""),
            }
            if status
            else None,
            "members": members,
        }

    @mcp.tool()
    async def asana_list_tasks(
        project_gid: str,
        assignee: Optional[str] = None,
        completed_since: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> dict:
        """List tasks in an Asana project with optional filters.

        Args:
            project_gid: The project GID to list tasks from.
            assignee: Filter by assignee (user GID or "me").
            completed_since: Only return tasks completed since this date (ISO 8601, e.g. "2024-01-01T00:00:00Z"). Use "now" to filter out all completed tasks.
            completed: Filter by completion status (true=completed only, false=incomplete only).

        Returns:
            List of tasks with gid, name, assignee, due date, and completion status.
        """
        params: dict = {
            "project": project_gid,
            "opt_fields": "name,completed,due_on,assignee.name,created_at,modified_at,notes",
        }
        if assignee:
            params["assignee"] = assignee
        if completed_since:
            params["completed_since"] = completed_since

        data = await _request("GET", "tasks", params=params)
        tasks = []
        for t in data.get("data", []):
            task_assignee = t.get("assignee")
            if completed is not None and t.get("completed") != completed:
                continue
            tasks.append({
                "gid": t["gid"],
                "name": t.get("name", ""),
                "completed": t.get("completed", False),
                "due_on": t.get("due_on"),
                "assignee": task_assignee.get("name", "") if task_assignee else None,
                "created_at": t.get("created_at"),
                "modified_at": t.get("modified_at"),
            })
        return {"project_gid": project_gid, "tasks": tasks}

    @mcp.tool()
    async def asana_get_task(task_gid: str) -> dict:
        """Get detailed information about a specific Asana task, including subtasks and comments.

        Args:
            task_gid: The task GID.

        Returns:
            Task details including name, notes, assignee, due date, subtasks, and comments (stories).
        """
        params = {
            "opt_fields": "name,notes,completed,due_on,due_at,start_on,assignee.name,"
            "projects.name,tags.name,created_at,modified_at,parent.name,"
            "num_subtasks,permalink_url",
        }
        data = await _request("GET", f"tasks/{task_gid}", params=params)
        t = data.get("data", {})
        task_assignee = t.get("assignee")
        parent = t.get("parent")

        # Fetch subtasks
        subtasks_data = await _request(
            "GET",
            f"tasks/{task_gid}/subtasks",
            params={"opt_fields": "name,completed,assignee.name,due_on"},
        )
        subtasks = []
        for s in subtasks_data.get("data", []):
            sub_assignee = s.get("assignee")
            subtasks.append({
                "gid": s["gid"],
                "name": s.get("name", ""),
                "completed": s.get("completed", False),
                "due_on": s.get("due_on"),
                "assignee": sub_assignee.get("name", "") if sub_assignee else None,
            })

        # Fetch comments (stories of type "comment")
        stories_data = await _request(
            "GET",
            f"tasks/{task_gid}/stories",
            params={"opt_fields": "type,text,created_by.name,created_at"},
        )
        comments = []
        for story in stories_data.get("data", []):
            if story.get("type") == "comment":
                author = story.get("created_by")
                comments.append({
                    "gid": story["gid"],
                    "text": story.get("text", ""),
                    "author": author.get("name", "") if author else None,
                    "created_at": story.get("created_at"),
                })

        projects = [
            {"gid": p["gid"], "name": p.get("name", "")}
            for p in t.get("projects", [])
        ]
        tags = [
            {"gid": tag["gid"], "name": tag.get("name", "")}
            for tag in t.get("tags", [])
        ]

        return {
            "gid": t.get("gid", task_gid),
            "name": t.get("name", ""),
            "notes": t.get("notes", ""),
            "completed": t.get("completed", False),
            "due_on": t.get("due_on"),
            "due_at": t.get("due_at"),
            "start_on": t.get("start_on"),
            "assignee": task_assignee.get("name", "") if task_assignee else None,
            "parent": {"gid": parent["gid"], "name": parent.get("name", "")} if parent else None,
            "projects": projects,
            "tags": tags,
            "created_at": t.get("created_at"),
            "modified_at": t.get("modified_at"),
            "permalink_url": t.get("permalink_url"),
            "subtasks": subtasks,
            "comments": comments,
        }

    @mcp.tool()
    async def asana_create_task(
        project_gid: str,
        name: str,
        notes: str = "",
        due_on: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> dict:
        """Create a new task in an Asana project.

        Args:
            project_gid: The project GID to add the task to.
            name: Task name/title.
            notes: Task description/notes (plain text).
            due_on: Due date in YYYY-MM-DD format (optional).
            assignee: Assignee user GID or "me" (optional).

        Returns:
            The created task with gid, name, and permalink.
        """
        task_data: dict = {
            "name": name,
            "projects": [project_gid],
        }
        if notes:
            task_data["notes"] = notes
        if due_on:
            task_data["due_on"] = due_on
        if assignee:
            task_data["assignee"] = assignee

        data = await _request("POST", "tasks", json={"data": task_data})
        t = data.get("data", {})
        return {
            "gid": t.get("gid", ""),
            "name": t.get("name", ""),
            "permalink_url": t.get("permalink_url", ""),
            "created_at": t.get("created_at"),
        }

    @mcp.tool()
    async def asana_update_task(
        task_gid: str,
        name: Optional[str] = None,
        notes: Optional[str] = None,
        due_on: Optional[str] = None,
        assignee: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> dict:
        """Update an existing Asana task.

        Args:
            task_gid: The task GID to update.
            name: New task name (optional).
            notes: New task notes/description (optional).
            due_on: New due date in YYYY-MM-DD format (optional).
            assignee: New assignee user GID or "me" (optional).
            completed: Set completion status (optional).

        Returns:
            The updated task with gid, name, and updated fields.
        """
        task_data: dict = {}
        if name is not None:
            task_data["name"] = name
        if notes is not None:
            task_data["notes"] = notes
        if due_on is not None:
            task_data["due_on"] = due_on
        if assignee is not None:
            task_data["assignee"] = assignee
        if completed is not None:
            task_data["completed"] = completed

        if not task_data:
            return {"status": "no_changes", "task_gid": task_gid}

        data = await _request("PUT", f"tasks/{task_gid}", json={"data": task_data})
        t = data.get("data", {})
        return {
            "gid": t.get("gid", task_gid),
            "name": t.get("name", ""),
            "completed": t.get("completed"),
            "due_on": t.get("due_on"),
            "modified_at": t.get("modified_at"),
            "status": "updated",
        }

    @mcp.tool()
    async def asana_list_users(workspace_gid: str) -> dict:
        """List users in an Asana workspace.

        Args:
            workspace_gid: The workspace GID to list users from.

        Returns:
            List of users with gid, name, and email.
        """
        params = {
            "workspace": workspace_gid,
            "opt_fields": "name,email",
        }
        data = await _request("GET", "users", params=params)
        users = []
        for u in data.get("data", []):
            users.append({
                "gid": u["gid"],
                "name": u.get("name", ""),
                "email": u.get("email", ""),
            })
        return {"workspace_gid": workspace_gid, "users": users}

    @mcp.tool()
    async def asana_add_comment(task_gid: str, text: str) -> dict:
        """Add a comment to an Asana task.

        Args:
            task_gid: The task GID to comment on.
            text: The comment text.

        Returns:
            The created comment (story) with gid, text, author, and timestamp.
        """
        data = await _request(
            "POST",
            f"tasks/{task_gid}/stories",
            json={"data": {"text": text}},
        )
        story = data.get("data", {})
        author = story.get("created_by")
        return {
            "gid": story.get("gid", ""),
            "text": story.get("text", ""),
            "author": author.get("name", "") if author else None,
            "created_at": story.get("created_at"),
            "task_gid": task_gid,
        }
