"""Vercel provider wrapping the Vercel REST API v9 (api.vercel.com)."""

import os
from typing import Optional

import requests
from mcp.server.fastmcp import FastMCP

API_BASE = "https://api.vercel.com"


def _get_api_token() -> str:
    """Return the Vercel API token from environment."""
    token = os.environ.get("VERCEL_TOKEN")
    if not token:
        raise RuntimeError("VERCEL_TOKEN environment variable is not set")
    return token


def _headers() -> dict:
    """Return standard Vercel Bearer authentication headers."""
    return {
        "Authorization": f"Bearer {_get_api_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the Vercel API."""
    url = f"{API_BASE}/{path.lstrip('/')}"
    resp = requests.request(
        method,
        url,
        headers=_headers(),
        timeout=30,
        **kwargs,
    )
    resp.raise_for_status()
    if resp.status_code == 204 or not resp.content:
        return {"success": True}
    return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Vercel tools with the MCP server."""

    @mcp.tool()
    def vercel_list_projects(
        limit: int = 20,
        since: Optional[int] = None,
        until: Optional[int] = None,
        search: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> dict:
        """List Vercel projects in the account or team.

        Args:
            limit: Maximum number of projects to return (default 20, max 100).
            since: Timestamp in milliseconds to list projects created after (optional).
            until: Timestamp in milliseconds to list projects created before (optional).
            search: Search projects by name (optional).
            team_id: Team ID to list projects for a specific team (optional).

        Returns:
            List of projects with id, name, framework, latest deployments, and repo info.
        """
        params: dict = {"limit": min(limit, 100)}
        if since is not None:
            params["since"] = since
        if until is not None:
            params["until"] = until
        if search:
            params["search"] = search
        if team_id:
            params["teamId"] = team_id
        data = _request("GET", "v9/projects", params=params)
        projects = []
        for p in data.get("projects", []):
            repo = p.get("link", {})
            latest = p.get("latestDeployments", [])
            latest_deploy = None
            if latest:
                d = latest[0]
                latest_deploy = {
                    "id": d.get("id", ""),
                    "url": d.get("url", ""),
                    "state": d.get("readyState", d.get("state", "")),
                    "created_at": d.get("createdAt", ""),
                }
            projects.append({
                "id": p.get("id", ""),
                "name": p.get("name", ""),
                "framework": p.get("framework"),
                "node_version": p.get("nodeVersion", ""),
                "repo": {
                    "type": repo.get("type", ""),
                    "repo": repo.get("repo", ""),
                    "org": repo.get("org", ""),
                } if repo else None,
                "latest_deployment": latest_deploy,
                "updated_at": p.get("updatedAt", ""),
                "created_at": p.get("createdAt", ""),
            })
        return {
            "count": len(projects),
            "projects": projects,
            "pagination": data.get("pagination", {}),
        }

    @mcp.tool()
    def vercel_get_project(
        project_id: str,
        team_id: Optional[str] = None,
    ) -> dict:
        """Get details of a specific Vercel project.

        Args:
            project_id: The project ID or name to retrieve.
            team_id: Team ID if the project belongs to a team (optional).

        Returns:
            Project details including name, framework, repo link, environment variables, and domains.
        """
        params: dict = {}
        if team_id:
            params["teamId"] = team_id
        data = _request("GET", f"v9/projects/{project_id}", params=params)
        repo = data.get("link", {})
        targets = data.get("targets", {})
        return {
            "id": data.get("id", ""),
            "name": data.get("name", ""),
            "framework": data.get("framework"),
            "node_version": data.get("nodeVersion", ""),
            "build_command": data.get("buildCommand"),
            "output_directory": data.get("outputDirectory"),
            "root_directory": data.get("rootDirectory"),
            "repo": {
                "type": repo.get("type", ""),
                "repo": repo.get("repo", ""),
                "org": repo.get("org", ""),
                "branch": repo.get("productionBranch", ""),
            } if repo else None,
            "production_deployment": {
                "id": targets.get("production", {}).get("id", ""),
                "url": targets.get("production", {}).get("url", ""),
                "state": targets.get("production", {}).get("readyState", ""),
            } if targets.get("production") else None,
            "auto_assign_custom_domains": data.get("autoAssignCustomDomains", True),
            "updated_at": data.get("updatedAt", ""),
            "created_at": data.get("createdAt", ""),
        }

    @mcp.tool()
    def vercel_list_deployments(
        project_id: Optional[str] = None,
        limit: int = 20,
        since: Optional[int] = None,
        until: Optional[int] = None,
        state: Optional[str] = None,
        target: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> dict:
        """List Vercel deployments, optionally filtered by project.

        Args:
            project_id: Filter by project ID or name (optional).
            limit: Maximum number of deployments to return (default 20, max 100).
            since: Timestamp in milliseconds to list deployments created after (optional).
            until: Timestamp in milliseconds to list deployments created before (optional).
            state: Filter by state: "BUILDING", "ERROR", "INITIALIZING", "QUEUED", "READY", "CANCELED" (optional).
            target: Filter by target: "production" or "preview" (optional).
            team_id: Team ID to list deployments for a specific team (optional).

        Returns:
            List of deployments with id, url, state, target, creator, and timestamps.
        """
        params: dict = {"limit": min(limit, 100)}
        if project_id:
            params["projectId"] = project_id
        if since is not None:
            params["since"] = since
        if until is not None:
            params["until"] = until
        if state:
            params["state"] = state
        if target:
            params["target"] = target
        if team_id:
            params["teamId"] = team_id
        data = _request("GET", "v6/deployments", params=params)
        deployments = []
        for d in data.get("deployments", []):
            creator = d.get("creator", {})
            deployments.append({
                "id": d.get("uid", ""),
                "name": d.get("name", ""),
                "url": d.get("url", ""),
                "state": d.get("readyState", d.get("state", "")),
                "target": d.get("target"),
                "source": d.get("source", ""),
                "creator": {
                    "uid": creator.get("uid", ""),
                    "username": creator.get("username", ""),
                } if creator else None,
                "created_at": d.get("createdAt", ""),
                "ready_at": d.get("ready", ""),
                "meta": {
                    "git_commit_sha": d.get("meta", {}).get("githubCommitSha", ""),
                    "git_commit_message": d.get("meta", {}).get("githubCommitMessage", ""),
                    "git_branch": d.get("meta", {}).get("githubCommitRef", ""),
                },
            })
        return {
            "count": len(deployments),
            "deployments": deployments,
            "pagination": data.get("pagination", {}),
        }

    @mcp.tool()
    def vercel_get_deployment(
        deployment_id: str,
        team_id: Optional[str] = None,
    ) -> dict:
        """Get details of a specific Vercel deployment.

        Args:
            deployment_id: The deployment ID or URL to retrieve.
            team_id: Team ID if the deployment belongs to a team (optional).

        Returns:
            Deployment details including state, URL, build logs, git metadata, and timing.
        """
        params: dict = {}
        if team_id:
            params["teamId"] = team_id
        data = _request("GET", f"v13/deployments/{deployment_id}", params=params)
        creator = data.get("creator", {})
        meta = data.get("meta", {})
        return {
            "id": data.get("id", ""),
            "name": data.get("name", ""),
            "url": data.get("url", ""),
            "state": data.get("readyState", ""),
            "target": data.get("target"),
            "source": data.get("source", ""),
            "creator": {
                "uid": creator.get("uid", ""),
                "username": creator.get("username", ""),
            } if creator else None,
            "git": {
                "sha": meta.get("githubCommitSha", ""),
                "message": meta.get("githubCommitMessage", ""),
                "branch": meta.get("githubCommitRef", ""),
                "repo": meta.get("githubRepo", ""),
                "org": meta.get("githubOrg", ""),
            },
            "alias_domains": data.get("alias", []),
            "regions": data.get("regions", []),
            "build_error": data.get("errorMessage"),
            "created_at": data.get("createdAt", ""),
            "building_at": data.get("buildingAt", ""),
            "ready_at": data.get("ready", ""),
        }

    @mcp.tool()
    def vercel_create_deployment(
        project_id: str,
        ref: Optional[str] = None,
        target: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> dict:
        """Trigger a new Vercel deployment for a project.

        This creates a new deployment by triggering a rebuild. For git-connected
        projects, you can specify a branch or commit ref.

        Args:
            project_id: The project ID or name to deploy.
            ref: Git ref (branch name or commit SHA) to deploy (optional, defaults to production branch).
            target: Deployment target: "production" or "preview" (optional, defaults to "production" if ref matches production branch).
            team_id: Team ID if the project belongs to a team (optional).

        Returns:
            Created deployment details including id, url, state, and target.
        """
        params: dict = {}
        if team_id:
            params["teamId"] = team_id
        payload: dict = {
            "name": project_id,
            "project": project_id,
        }
        if ref:
            payload["gitSource"] = {
                "ref": ref,
                "type": "github",
            }
        if target:
            payload["target"] = target
        data = _request("POST", "v13/deployments", params=params, json=payload)
        return {
            "id": data.get("id", ""),
            "url": data.get("url", ""),
            "state": data.get("readyState", data.get("status", "")),
            "target": data.get("target"),
            "alias_domains": data.get("alias", []),
            "created_at": data.get("createdAt", ""),
        }

    @mcp.tool()
    def vercel_list_domains(
        project_id: str,
        team_id: Optional[str] = None,
    ) -> dict:
        """List domains configured for a Vercel project.

        Args:
            project_id: The project ID or name to list domains for.
            team_id: Team ID if the project belongs to a team (optional).

        Returns:
            List of domains with name, redirect target, and git branch linkage.
        """
        params: dict = {}
        if team_id:
            params["teamId"] = team_id
        data = _request("GET", f"v9/projects/{project_id}/domains", params=params)
        domains = []
        for d in data.get("domains", []):
            domains.append({
                "name": d.get("name", ""),
                "redirect": d.get("redirect"),
                "redirect_status_code": d.get("redirectStatusCode"),
                "git_branch": d.get("gitBranch"),
                "created_at": d.get("createdAt", ""),
                "updated_at": d.get("updatedAt", ""),
            })
        return {"domains": domains}

    @mcp.tool()
    def vercel_list_environment_variables(
        project_id: str,
        team_id: Optional[str] = None,
    ) -> dict:
        """List environment variables for a Vercel project.

        Args:
            project_id: The project ID or name to list environment variables for.
            team_id: Team ID if the project belongs to a team (optional).

        Returns:
            List of environment variables with key, target environments, and type (not values for security).
        """
        params: dict = {}
        if team_id:
            params["teamId"] = team_id
        data = _request("GET", f"v9/projects/{project_id}/env", params=params)
        env_vars = []
        for e in data.get("envs", []):
            env_vars.append({
                "id": e.get("id", ""),
                "key": e.get("key", ""),
                "target": e.get("target", []),
                "type": e.get("type", ""),
                "git_branch": e.get("gitBranch"),
                "created_at": e.get("createdAt", ""),
                "updated_at": e.get("updatedAt", ""),
            })
        return {"env_vars": env_vars}
