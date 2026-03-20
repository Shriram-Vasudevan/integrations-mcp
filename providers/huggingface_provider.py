"""HuggingFace provider using the huggingface_hub SDK."""

import os
from typing import Optional

from mcp.server.fastmcp import FastMCP


def _get_api():
    """Return an authenticated HfApi instance."""
    from huggingface_hub import HfApi
    token = os.environ.get("HUGGINGFACE_API_KEY")
    if not token:
        raise RuntimeError("HUGGINGFACE_API_KEY environment variable is not set")
    return HfApi(token=token)


def _model_to_dict(m) -> dict:
    """Convert a ModelInfo object to a serialisable dict."""
    return {
        "id": m.id,
        "author": m.author or "",
        "pipeline_tag": m.pipeline_tag,
        "library_name": m.library_name,
        "downloads": m.downloads or 0,
        "likes": m.likes or 0,
        "tags": list(m.tags) if m.tags else [],
        "last_modified": str(m.last_modified) if m.last_modified else "",
        "private": m.private,
    }


def _dataset_to_dict(d) -> dict:
    """Convert a DatasetInfo object to a serialisable dict."""
    return {
        "id": d.id,
        "author": d.author or "",
        "downloads": d.downloads or 0,
        "likes": d.likes or 0,
        "tags": list(d.tags) if d.tags else [],
        "last_modified": str(d.last_modified) if d.last_modified else "",
        "private": d.private,
    }


def _space_to_dict(s) -> dict:
    """Convert a SpaceInfo object to a serialisable dict."""
    return {
        "id": s.id,
        "author": s.author or "",
        "sdk": getattr(s, "sdk", None),
        "likes": s.likes or 0,
        "last_modified": str(s.last_modified) if s.last_modified else "",
        "private": s.private,
    }


def register(mcp: FastMCP) -> None:
    """Register HuggingFace tools with the MCP server."""

    @mcp.tool()
    def huggingface_search_models(
        query: str,
        filter_task: Optional[str] = None,
        filter_library: Optional[str] = None,
        sort: str = "downloads",
        direction: int = -1,
        limit: int = 20,
    ) -> dict:
        """Search for models on the HuggingFace Hub.

        Args:
            query: Search query string.
            filter_task: Filter by pipeline task (e.g. "text-generation", "image-classification").
            filter_library: Filter by library (e.g. "transformers", "diffusers", "pytorch").
            sort: Sort field — "downloads", "likes", "created_at", "lastModified" (default "downloads").
            direction: Sort direction — -1 for descending, 1 for ascending (default -1).
            limit: Number of results to return, max 100 (default 20).

        Returns:
            List of matching models with id, task, downloads, likes, and tags.
        """
        api = _get_api()
        models = list(api.list_models(
            search=query,
            pipeline_tag=filter_task,
            library=filter_library,
            sort=sort,
            direction=direction,
            limit=min(limit, 100),
        ))
        return {
            "models": [_model_to_dict(m) for m in models],
            "count": len(models),
        }

    @mcp.tool()
    def huggingface_get_model_info(model_id: str) -> dict:
        """Get detailed information about a specific HuggingFace model.

        Args:
            model_id: The model ID (e.g. "google/flan-t5-base", "meta-llama/Llama-2-7b").

        Returns:
            Model details including tags, downloads, pipeline task, config, and files.
        """
        api = _get_api()
        m = api.model_info(model_id)
        card_data = m.card_data or {}
        card_dict = card_data if isinstance(card_data, dict) else (card_data.__dict__ if hasattr(card_data, "__dict__") else {})
        siblings = m.siblings or []
        return {
            "id": m.id,
            "author": m.author or "",
            "pipeline_tag": m.pipeline_tag,
            "library_name": m.library_name,
            "tags": list(m.tags) if m.tags else [],
            "downloads": m.downloads or 0,
            "likes": m.likes or 0,
            "private": m.private,
            "gated": getattr(m, "gated", False),
            "last_modified": str(m.last_modified) if m.last_modified else "",
            "created_at": str(m.created_at) if m.created_at else "",
            "license": card_dict.get("license"),
            "language": card_dict.get("language"),
            "datasets": card_dict.get("datasets", []),
            "siblings": [
                {"filename": s.rfilename}
                for s in siblings[:20]
            ],
        }

    @mcp.tool()
    def huggingface_list_datasets(
        search: Optional[str] = None,
        author: Optional[str] = None,
        sort: str = "downloads",
        direction: int = -1,
        limit: int = 20,
    ) -> dict:
        """List datasets on the HuggingFace Hub with optional filters.

        Args:
            search: Search query to filter datasets by name.
            author: Filter by dataset author/organization.
            sort: Sort field — "downloads", "likes", "created_at", "lastModified" (default "downloads").
            direction: Sort direction — -1 for descending, 1 for ascending (default -1).
            limit: Number of results to return, max 100 (default 20).

        Returns:
            List of datasets with id, author, downloads, and tags.
        """
        api = _get_api()
        datasets = list(api.list_datasets(
            search=search or "",
            author=author,
            sort=sort,
            direction=direction,
            limit=min(limit, 100),
        ))
        return {
            "datasets": [_dataset_to_dict(d) for d in datasets],
            "count": len(datasets),
        }

    @mcp.tool()
    def huggingface_search_datasets(
        query: str,
        author: Optional[str] = None,
        sort: str = "downloads",
        direction: int = -1,
        limit: int = 20,
    ) -> dict:
        """Search for datasets on the HuggingFace Hub with full-text search.

        Args:
            query: Search query string.
            author: Filter by dataset author/organization.
            sort: Sort field — "downloads", "likes", "created_at", "lastModified" (default "downloads").
            direction: Sort direction — -1 for descending, 1 for ascending (default -1).
            limit: Number of results to return, max 100 (default 20).

        Returns:
            List of matching datasets with id, author, downloads, likes, and tags.
        """
        api = _get_api()
        datasets = list(api.list_datasets(
            search=query,
            author=author,
            sort=sort,
            direction=direction,
            limit=min(limit, 100),
        ))
        return {
            "datasets": [_dataset_to_dict(d) for d in datasets],
            "count": len(datasets),
        }

    @mcp.tool()
    def huggingface_get_dataset_info(dataset_id: str) -> dict:
        """Get detailed information about a specific HuggingFace dataset.

        Args:
            dataset_id: The dataset ID (e.g. "squad", "glue", "imdb").

        Returns:
            Dataset details including tags, downloads, license, and file listing.
        """
        api = _get_api()
        d = api.dataset_info(dataset_id)
        card_data = d.card_data or {}
        card_dict = card_data if isinstance(card_data, dict) else (card_data.__dict__ if hasattr(card_data, "__dict__") else {})
        siblings = d.siblings or []
        return {
            "id": d.id,
            "author": d.author or "",
            "tags": list(d.tags) if d.tags else [],
            "downloads": d.downloads or 0,
            "likes": d.likes or 0,
            "private": d.private,
            "gated": getattr(d, "gated", False),
            "last_modified": str(d.last_modified) if d.last_modified else "",
            "created_at": str(d.created_at) if d.created_at else "",
            "license": card_dict.get("license"),
            "language": card_dict.get("language"),
            "task_categories": card_dict.get("task_categories", []),
            "size_categories": card_dict.get("size_categories", []),
            "siblings": [
                {"filename": s.rfilename}
                for s in siblings[:20]
            ],
        }

    @mcp.tool()
    def huggingface_list_spaces(
        search: Optional[str] = None,
        author: Optional[str] = None,
        sort: str = "likes",
        direction: int = -1,
        limit: int = 20,
    ) -> dict:
        """List Spaces on the HuggingFace Hub with optional filters.

        Args:
            search: Search query to filter spaces by name.
            author: Filter by space author/organization.
            sort: Sort field — "likes", "created_at", "lastModified" (default "likes").
            direction: Sort direction — -1 for descending, 1 for ascending (default -1).
            limit: Number of results to return, max 100 (default 20).

        Returns:
            List of spaces with id, author, sdk, likes, and metadata.
        """
        api = _get_api()
        spaces = list(api.list_spaces(
            search=search or "",
            author=author,
            sort=sort,
            direction=direction,
            limit=min(limit, 100),
        ))
        return {
            "spaces": [_space_to_dict(s) for s in spaces],
            "count": len(spaces),
        }
