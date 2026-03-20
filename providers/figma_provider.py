"""Figma provider wrapping the Figma REST API (api.figma.com)."""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

FIGMA_API_BASE = "https://api.figma.com/v1"


def _get_token() -> str:
    """Return the Figma access token from environment."""
    token = os.environ.get("FIGMA_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("FIGMA_ACCESS_TOKEN environment variable is not set")
    return token


def _headers() -> dict:
    return {
        "X-Figma-Token": _get_token(),
        "Content-Type": "application/json",
    }


async def _request(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated request to the Figma REST API.

    Args:
        method: HTTP method (GET or POST).
        path: API path (e.g. "files/abc123").
        **kwargs: Extra arguments passed to httpx (params, json, etc.).

    Returns:
        Parsed JSON response from Figma.

    Raises:
        httpx.HTTPStatusError: If the API returns a non-2xx status.
    """
    url = f"{FIGMA_API_BASE}/{path.lstrip('/')}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=_headers(), timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register Figma tools with the MCP server."""

    # ── Projects ───────────────────────────────────────────────────────

    @mcp.tool()
    async def figma_list_projects(team_id: str) -> dict:
        """List all projects for a Figma team.

        Args:
            team_id: The Figma team ID.

        Returns:
            List of projects with id and name.
        """
        data = await _request("GET", f"teams/{team_id}/projects")
        projects = []
        for p in data.get("projects", []):
            projects.append({
                "id": p.get("id"),
                "name": p.get("name"),
            })
        return {"projects": projects}

    # ── Files ──────────────────────────────────────────────────────────

    @mcp.tool()
    async def figma_list_files(project_id: str) -> dict:
        """List all files in a Figma project.

        Args:
            project_id: The Figma project ID.

        Returns:
            List of files with key, name, thumbnail_url, and last_modified.
        """
        data = await _request("GET", f"projects/{project_id}/files")
        files = []
        for f in data.get("files", []):
            files.append({
                "key": f.get("key"),
                "name": f.get("name"),
                "thumbnail_url": f.get("thumbnail_url"),
                "last_modified": f.get("last_modified"),
            })
        return {"files": files}

    @mcp.tool()
    async def figma_get_file(file_key: str) -> dict:
        """Get a Figma file including its full document node tree.

        Args:
            file_key: The file key (from the file URL or listing).

        Returns:
            File metadata (name, lastModified, version) and the full document
            node tree under the 'document' key.
        """
        data = await _request("GET", f"files/{file_key}")
        return {
            "name": data.get("name"),
            "lastModified": data.get("lastModified"),
            "version": data.get("version"),
            "document": data.get("document"),
        }

    @mcp.tool()
    async def figma_get_file_nodes(
        file_key: str,
        node_ids: list[str],
    ) -> dict:
        """Get specific nodes from a Figma file by their IDs.

        Args:
            file_key: The file key.
            node_ids: List of node IDs to retrieve (e.g. ["1:2", "3:4"]).

        Returns:
            Dict mapping each node ID to its node data.
        """
        ids_param = ",".join(node_ids)
        data = await _request("GET", f"files/{file_key}/nodes", params={"ids": ids_param})
        nodes = {}
        for node_id, node_data in data.get("nodes", {}).items():
            nodes[node_id] = node_data
        return {"nodes": nodes}

    # ── Components ─────────────────────────────────────────────────────

    @mcp.tool()
    async def figma_get_file_components(file_key: str) -> dict:
        """List all components in a Figma file.

        Args:
            file_key: The file key.

        Returns:
            List of components with key, name, description, and containing_frame.
        """
        data = await _request("GET", f"files/{file_key}/components")
        components = []
        for c in data.get("meta", {}).get("components", []):
            components.append({
                "key": c.get("key"),
                "name": c.get("name"),
                "description": c.get("description"),
                "containing_frame": c.get("containing_frame", {}).get("name"),
                "node_id": c.get("node_id"),
            })
        return {"components": components}

    # ── Comments ───────────────────────────────────────────────────────

    @mcp.tool()
    async def figma_get_comments(file_key: str) -> dict:
        """Get all comments on a Figma file.

        Args:
            file_key: The file key.

        Returns:
            List of comments with id, message, user, created_at, and resolved_at.
        """
        data = await _request("GET", f"files/{file_key}/comments")
        comments = []
        for c in data.get("comments", []):
            user = c.get("user", {})
            comments.append({
                "id": c.get("id"),
                "message": c.get("message"),
                "user": user.get("handle"),
                "created_at": c.get("created_at"),
                "resolved_at": c.get("resolved_at"),
                "order_id": c.get("order_id"),
            })
        return {"comments": comments}

    @mcp.tool()
    async def figma_post_comment(
        file_key: str,
        message: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> dict:
        """Post a comment on a Figma file.

        Args:
            file_key: The file key.
            message: The comment message text.
            x: Optional x coordinate for pinning the comment on the canvas.
            y: Optional y coordinate for pinning the comment on the canvas.

        Returns:
            The created comment with id, message, and user.
        """
        payload: dict = {"message": message}
        if x is not None and y is not None:
            payload["client_meta"] = {"x": x, "y": y}
        data = await _request("POST", f"files/{file_key}/comments", json=payload)
        user = data.get("user", {})
        return {
            "id": data.get("id"),
            "message": data.get("message"),
            "user": user.get("handle"),
            "created_at": data.get("created_at"),
        }

    # ── Image Export ───────────────────────────────────────────────────

    @mcp.tool()
    async def figma_get_images(
        file_key: str,
        node_ids: list[str],
        format: str = "png",
        scale: Optional[float] = None,
    ) -> dict:
        """Export images of specific nodes from a Figma file.

        Args:
            file_key: The file key.
            node_ids: List of node IDs to export (e.g. ["1:2", "3:4"]).
            format: Image format — "png", "svg", or "pdf" (default "png").
            scale: Image scale factor (0.01-4, default 1). Only applies to png.

        Returns:
            Dict mapping each node ID to its image download URL.
        """
        valid_formats = {"png", "svg", "pdf"}
        if format not in valid_formats:
            raise ValueError(f"format must be one of {valid_formats}, got '{format}'")

        params: dict = {
            "ids": ",".join(node_ids),
            "format": format,
        }
        if scale is not None and format == "png":
            params["scale"] = scale

        data = await _request("GET", f"images/{file_key}", params=params)
        return {
            "images": data.get("images", {}),
            "err": data.get("err"),
        }
