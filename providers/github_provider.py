"""GitHub provider wrapping the GitHub REST API v3 using async httpx."""

import base64
import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

GITHUB_API_BASE = "https://api.github.com"


def _get_token() -> str:
    """Return the GitHub personal access token from environment."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN environment variable is not set")
    return token


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _request(method: str, path: str, **kwargs) -> dict | list:
    """Make an authenticated request to the GitHub REST API v3."""
    url = f"{GITHUB_API_BASE}/{path.lstrip('/')}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            url,
            headers=_headers(),
            timeout=30,
            **kwargs,
        )
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {"status": "ok"}
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register GitHub tools with the MCP server."""

    @mcp.tool()
    async def github_create_issue(
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        assignees: Optional[list[str]] = None,
        labels: Optional[list[str]] = None,
        milestone: Optional[int] = None,
    ) -> dict:
        """Create a new issue in a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: Issue title.
            body: Issue body in Markdown (optional).
            assignees: List of usernames to assign (optional).
            labels: List of label names (optional).
            milestone: Milestone ID number (optional).

        Returns:
            Created issue number, URL, and title.
        """
        payload: dict = {"title": title}
        if body:
            payload["body"] = body
        if assignees:
            payload["assignees"] = assignees
        if labels:
            payload["labels"] = labels
        if milestone is not None:
            payload["milestone"] = milestone
        data = await _request("POST", f"repos/{owner}/{repo}/issues", json=payload)
        return {
            "number": data["number"],
            "title": data["title"],
            "html_url": data["html_url"],
            "state": data["state"],
        }

    @mcp.tool()
    async def github_comment_on_issue(
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> dict:
        """Create a comment on an issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: The issue number.
            body: Comment body in Markdown.

        Returns:
            Created comment ID, URL, and body excerpt.
        """
        data = await _request(
            "POST",
            f"repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        return {
            "id": data["id"],
            "html_url": data["html_url"],
            "body": data["body"][:200] if data.get("body") else "",
            "user": data["user"]["login"],
            "created_at": data.get("created_at", ""),
        }

    @mcp.tool()
    async def github_create_pr_comment(
        owner: str,
        repo: str,
        pull_number: int,
        body: str,
    ) -> dict:
        """Create a comment on a pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: The pull request number.
            body: Comment body in Markdown.

        Returns:
            Created comment ID, URL, and body excerpt.
        """
        data = await _request(
            "POST",
            f"repos/{owner}/{repo}/issues/{pull_number}/comments",
            json={"body": body},
        )
        return {
            "id": data["id"],
            "html_url": data["html_url"],
            "body": data["body"][:200] if data.get("body") else "",
            "user": data["user"]["login"],
            "created_at": data.get("created_at", ""),
        }

    @mcp.tool()
    async def github_get_file_contents(
        owner: str,
        repo: str,
        path: str,
        ref: str = "",
    ) -> dict:
        """Get the contents of a file or directory from a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: Path to the file or directory in the repository.
            ref: Branch, tag, or commit SHA (optional, defaults to default branch).

        Returns:
            File content (decoded), name, path, size, and SHA. For directories, a list of entries.
        """
        params = {}
        if ref:
            params["ref"] = ref
        data = await _request("GET", f"repos/{owner}/{repo}/contents/{path.lstrip('/')}", params=params)
        if isinstance(data, list):
            entries = []
            for entry in data:
                entries.append({
                    "name": entry["name"],
                    "path": entry["path"],
                    "type": entry["type"],
                    "size": entry.get("size", 0),
                    "sha": entry["sha"],
                })
            return {"type": "directory", "entries": entries, "count": len(entries)}
        content = ""
        if data.get("content") and data.get("encoding") == "base64":
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return {
            "type": "file",
            "name": data["name"],
            "path": data["path"],
            "size": data.get("size", 0),
            "sha": data["sha"],
            "content": content,
            "encoding": "utf-8",
            "html_url": data.get("html_url", ""),
        }

    @mcp.tool()
    async def github_get_issue(owner: str, repo: str, issue_number: int) -> dict:
        """Get details of a specific issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: The issue number.

        Returns:
            Full issue details including body, labels, assignees, and milestone.
        """
        i = await _request("GET", f"repos/{owner}/{repo}/issues/{issue_number}")
        milestone = i.get("milestone")
        return {
            "number": i["number"],
            "title": i["title"],
            "state": i["state"],
            "body": i.get("body"),
            "user": i["user"]["login"],
            "assignees": [a["login"] for a in i.get("assignees", [])],
            "labels": [l["name"] for l in i.get("labels", [])],
            "comments": i.get("comments", 0),
            "milestone": milestone.get("title") if milestone else None,
            "html_url": i.get("html_url", ""),
            "created_at": i.get("created_at", ""),
            "updated_at": i.get("updated_at", ""),
            "closed_at": i.get("closed_at"),
        }

    @mcp.tool()
    async def github_get_pr(owner: str, repo: str, pull_number: int) -> dict:
        """Get details of a specific pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: The pull request number.

        Returns:
            Full pull request details including diff stats, review status, and merge info.
        """
        p = await _request("GET", f"repos/{owner}/{repo}/pulls/{pull_number}")
        return {
            "number": p["number"],
            "title": p["title"],
            "state": p["state"],
            "body": p.get("body"),
            "user": p["user"]["login"],
            "head": p["head"]["ref"],
            "base": p["base"]["ref"],
            "draft": p.get("draft", False),
            "mergeable": p.get("mergeable"),
            "merged": p.get("merged", False),
            "merged_by": p.get("merged_by", {}).get("login") if p.get("merged_by") else None,
            "commits": p.get("commits", 0),
            "additions": p.get("additions", 0),
            "deletions": p.get("deletions", 0),
            "changed_files": p.get("changed_files", 0),
            "html_url": p.get("html_url", ""),
            "created_at": p.get("created_at", ""),
            "updated_at": p.get("updated_at", ""),
            "merged_at": p.get("merged_at"),
            "closed_at": p.get("closed_at"),
        }

    @mcp.tool()
    async def github_get_repo(owner: str, repo: str) -> dict:
        """Get detailed information about a specific repository.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.

        Returns:
            Full repository details including description, stats, and URLs.
        """
        r = await _request("GET", f"repos/{owner}/{repo}")
        return {
            "full_name": r["full_name"],
            "name": r["name"],
            "owner": r["owner"]["login"],
            "private": r["private"],
            "description": r.get("description"),
            "language": r.get("language"),
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "watchers": r.get("watchers_count", 0),
            "open_issues": r.get("open_issues_count", 0),
            "default_branch": r.get("default_branch", "main"),
            "topics": r.get("topics", []),
            "html_url": r.get("html_url", ""),
            "clone_url": r.get("clone_url", ""),
            "created_at": r.get("created_at", ""),
            "updated_at": r.get("updated_at", ""),
            "pushed_at": r.get("pushed_at", ""),
            "license": r.get("license", {}).get("spdx_id") if r.get("license") else None,
            "archived": r.get("archived", False),
            "disabled": r.get("disabled", False),
        }

    @mcp.tool()
    async def github_list_commits(
        owner: str,
        repo: str,
        sha: str = "",
        path: str = "",
        author: str = "",
        since: str = "",
        until: str = "",
        per_page: int = 30,
        page: int = 1,
    ) -> dict:
        """List commits for a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            sha: Branch name or commit SHA to start from (optional, defaults to default branch).
            path: Only commits containing this file path (optional).
            author: GitHub username or email to filter by author (optional).
            since: ISO 8601 timestamp — only commits after this date (optional).
            until: ISO 8601 timestamp — only commits before this date (optional).
            per_page: Results per page, max 100 (default 30).
            page: Page number (default 1).

        Returns:
            List of commits with SHA, message, author, and date.
        """
        params = {"per_page": min(per_page, 100), "page": page}
        if sha:
            params["sha"] = sha
        if path:
            params["path"] = path
        if author:
            params["author"] = author
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        data = await _request("GET", f"repos/{owner}/{repo}/commits", params=params)
        commits = []
        for c in data:
            commit = c.get("commit", {})
            author_info = commit.get("author", {})
            commits.append({
                "sha": c["sha"],
                "message": commit.get("message", ""),
                "author": author_info.get("name", ""),
                "author_email": author_info.get("email", ""),
                "date": author_info.get("date", ""),
                "committer": commit.get("committer", {}).get("name", ""),
                "html_url": c.get("html_url", ""),
            })
        return {"commits": commits, "count": len(commits)}

    @mcp.tool()
    async def github_list_issues(
        owner: str,
        repo: str,
        state: str = "open",
        labels: str = "",
        assignee: str = "",
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 30,
        page: int = 1,
    ) -> dict:
        """List issues for a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: Issue state — "open", "closed", or "all" (default "open").
            labels: Comma-separated label names to filter by.
            assignee: Username to filter by assignee, or "none"/"*".
            sort: Sort field — "created", "updated", "comments" (default "created").
            direction: Sort direction — "asc" or "desc" (default "desc").
            per_page: Results per page, max 100 (default 30).
            page: Page number (default 1).

        Returns:
            List of issues with key fields.
        """
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": min(per_page, 100),
            "page": page,
        }
        if labels:
            params["labels"] = labels
        if assignee:
            params["assignee"] = assignee
        data = await _request("GET", f"repos/{owner}/{repo}/issues", params=params)
        issues = []
        for i in data:
            if i.get("pull_request"):
                continue
            issues.append({
                "number": i["number"],
                "title": i["title"],
                "state": i["state"],
                "user": i["user"]["login"],
                "assignees": [a["login"] for a in i.get("assignees", [])],
                "labels": [l["name"] for l in i.get("labels", [])],
                "comments": i.get("comments", 0),
                "created_at": i.get("created_at", ""),
                "updated_at": i.get("updated_at", ""),
            })
        return {"issues": issues, "count": len(issues)}

    @mcp.tool()
    async def github_list_prs(
        owner: str,
        repo: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc",
        head: str = "",
        base: str = "",
        per_page: int = 30,
        page: int = 1,
    ) -> dict:
        """List pull requests for a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: PR state — "open", "closed", "all" (default "open").
            sort: Sort field — "created", "updated", "popularity", "long-running" (default "created").
            direction: Sort direction — "asc" or "desc" (default "desc").
            head: Filter by head branch (format: "user:branch" or "branch").
            base: Filter by base branch name.
            per_page: Results per page, max 100 (default 30).
            page: Page number (default 1).

        Returns:
            List of pull requests with key metadata.
        """
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": min(per_page, 100),
            "page": page,
        }
        if head:
            params["head"] = head
        if base:
            params["base"] = base
        data = await _request("GET", f"repos/{owner}/{repo}/pulls", params=params)
        prs = []
        for p in data:
            prs.append({
                "number": p["number"],
                "title": p["title"],
                "state": p["state"],
                "user": p["user"]["login"],
                "head": p["head"]["ref"],
                "base": p["base"]["ref"],
                "draft": p.get("draft", False),
                "merged_at": p.get("merged_at"),
                "created_at": p.get("created_at", ""),
                "updated_at": p.get("updated_at", ""),
            })
        return {"pull_requests": prs, "count": len(prs)}

    @mcp.tool()
    async def github_list_repos(
        owner: Optional[str] = None,
        type: str = "all",
        sort: str = "updated",
        per_page: int = 30,
        page: int = 1,
    ) -> dict:
        """List repositories for the authenticated user or a specific owner.

        Args:
            owner: GitHub username or org. If omitted, lists repos for the authenticated user.
            type: Filter type — "all", "owner", "public", "private", "member" (default "all").
            sort: Sort field — "created", "updated", "pushed", "full_name" (default "updated").
            per_page: Results per page, max 100 (default 30).
            page: Page number (default 1).

        Returns:
            List of repositories with key metadata.
        """
        params = {"type": type, "sort": sort, "per_page": min(per_page, 100), "page": page}
        if owner:
            data = await _request("GET", f"users/{owner}/repos", params=params)
        else:
            data = await _request("GET", "user/repos", params=params)
        repos = []
        for r in data:
            repos.append({
                "full_name": r["full_name"],
                "name": r["name"],
                "owner": r["owner"]["login"],
                "private": r["private"],
                "description": r.get("description"),
                "language": r.get("language"),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "open_issues": r.get("open_issues_count", 0),
                "default_branch": r.get("default_branch", "main"),
                "updated_at": r.get("updated_at", ""),
            })
        return {"repos": repos, "count": len(repos)}

    @mcp.tool()
    async def github_update_issue(
        owner: str,
        repo: str,
        issue_number: int,
        title: str = "",
        body: str = "",
        state: str = "",
        assignees: Optional[list[str]] = None,
        labels: Optional[list[str]] = None,
        milestone: Optional[int] = None,
    ) -> dict:
        """Update an existing issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: The issue number to update.
            title: New title (optional, leave empty to keep current).
            body: New body in Markdown (optional).
            state: New state — "open" or "closed" (optional).
            assignees: New list of assignee usernames (optional, replaces existing).
            labels: New list of label names (optional, replaces existing).
            milestone: New milestone ID, or 0 to clear (optional).

        Returns:
            Updated issue number and state.
        """
        payload: dict = {}
        if title:
            payload["title"] = title
        if body:
            payload["body"] = body
        if state:
            payload["state"] = state
        if assignees is not None:
            payload["assignees"] = assignees
        if labels is not None:
            payload["labels"] = labels
        if milestone is not None:
            payload["milestone"] = milestone if milestone != 0 else None
        if not payload:
            return {"status": "no_changes", "issue_number": issue_number}
        data = await _request("PATCH", f"repos/{owner}/{repo}/issues/{issue_number}", json=payload)
        return {
            "number": data["number"],
            "title": data["title"],
            "state": data["state"],
            "html_url": data["html_url"],
            "status": "updated",
        }

    @mcp.tool()
    async def github_create_or_update_file(
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "",
        sha: str = "",
    ) -> dict:
        """Create or update a file in a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: Path for the file in the repository.
            content: File content as a UTF-8 string (will be base64-encoded automatically).
            message: Commit message.
            branch: Branch to commit to (optional, defaults to default branch).
            sha: SHA of the file being replaced (required for updates, omit for new files).

        Returns:
            Commit SHA, file path, and html_url of the committed file.
        """
        payload: dict = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        }
        if branch:
            payload["branch"] = branch
        if sha:
            payload["sha"] = sha
        data = await _request("PUT", f"repos/{owner}/{repo}/contents/{path.lstrip('/')}", json=payload)
        file_info = data.get("content", {})
        commit_info = data.get("commit", {})
        return {
            "path": file_info.get("path", path),
            "sha": file_info.get("sha", ""),
            "commit_sha": commit_info.get("sha", ""),
            "html_url": file_info.get("html_url", ""),
            "status": "created" if not sha else "updated",
        }

    @mcp.tool()
    async def github_list_branches(
        owner: str,
        repo: str,
        protected: Optional[bool] = None,
        per_page: int = 30,
        page: int = 1,
    ) -> dict:
        """List branches for a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            protected: If True, only return protected branches. If False, only unprotected (optional).
            per_page: Results per page, max 100 (default 30).
            page: Page number (default 1).

        Returns:
            List of branches with name, SHA, and protection status.
        """
        params = {"per_page": min(per_page, 100), "page": page}
        if protected is not None:
            params["protected"] = str(protected).lower()
        data = await _request("GET", f"repos/{owner}/{repo}/branches", params=params)
        branches = []
        for b in data:
            branches.append({
                "name": b["name"],
                "sha": b["commit"]["sha"],
                "protected": b.get("protected", False),
            })
        return {"branches": branches, "count": len(branches)}

    @mcp.tool()
    async def github_search_code(
        query: str,
        per_page: int = 30,
        page: int = 1,
    ) -> dict:
        """Search for code across GitHub repositories.

        Args:
            query: Search query using GitHub code search syntax.
                   Examples: "addClass repo:jquery/jquery", "user:defunkt extension:rb",
                   "shogun language:python".
            per_page: Results per page, max 100 (default 30).
            page: Page number (default 1).

        Returns:
            Matching code results with file path, repository, and matched text fragment.
        """
        params = {"q": query, "per_page": min(per_page, 100), "page": page}
        data = await _request("GET", "search/code", params=params)
        items = []
        for item in data.get("items", []):
            repo = item.get("repository", {})
            items.append({
                "name": item["name"],
                "path": item["path"],
                "sha": item["sha"],
                "html_url": item.get("html_url", ""),
                "repository": repo.get("full_name", ""),
                "score": item.get("score", 0),
            })
        return {
            "total_count": data.get("total_count", 0),
            "items": items,
            "count": len(items),
        }

    @mcp.tool()
    async def github_search_issues(
        query: str,
        sort: str = "",
        order: str = "desc",
        per_page: int = 30,
        page: int = 1,
    ) -> dict:
        """Search for issues and pull requests across GitHub.

        Args:
            query: Search query using GitHub issues search syntax.
                   Examples: "repo:owner/name is:open label:bug",
                   "author:user type:pr is:merged".
            sort: Sort field — "comments", "reactions", "created", "updated", or "" for best match.
            order: Sort order — "asc" or "desc" (default "desc").
            per_page: Results per page, max 100 (default 30).
            page: Page number (default 1).

        Returns:
            Matching issues/PRs with title, state, labels, and repository info.
        """
        params = {"q": query, "order": order, "per_page": min(per_page, 100), "page": page}
        if sort:
            params["sort"] = sort
        data = await _request("GET", "search/issues", params=params)
        items = []
        for item in data.get("items", []):
            repo_url = item.get("repository_url", "")
            repo_name = "/".join(repo_url.rsplit("/", 2)[-2:]) if repo_url else ""
            items.append({
                "number": item["number"],
                "title": item["title"],
                "state": item["state"],
                "user": item["user"]["login"],
                "labels": [l["name"] for l in item.get("labels", [])],
                "repository": repo_name,
                "is_pull_request": "pull_request" in item,
                "comments": item.get("comments", 0),
                "html_url": item.get("html_url", ""),
                "created_at": item.get("created_at", ""),
                "updated_at": item.get("updated_at", ""),
                "closed_at": item.get("closed_at"),
            })
        return {
            "total_count": data.get("total_count", 0),
            "items": items,
            "count": len(items),
        }
