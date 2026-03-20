"""Open Trivia Database provider — free, no auth required."""

import html
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

OPENTDB_API_URL = "https://opentdb.com/api.php"
OPENTDB_CATEGORIES_URL = "https://opentdb.com/api_category.php"

RESPONSE_CODES = {
    0: "Success",
    1: "No Results — not enough questions for your query.",
    2: "Invalid Parameter — bad argument passed.",
    3: "Token Not Found",
    4: "Token Empty — all questions exhausted for this query.",
    5: "Rate Limit — too many requests, try again later.",
}


def _decode(text: str) -> str:
    """Decode HTML entities in API responses."""
    return html.unescape(text)


def register(mcp: FastMCP) -> None:
    """Register trivia tools with the MCP server."""

    @mcp.tool()
    async def get_trivia_questions(
        amount: int = 5,
        category: Optional[int] = None,
        difficulty: Optional[str] = None,
    ) -> dict:
        """Fetch trivia questions from the Open Trivia Database.

        Args:
            amount: Number of questions to retrieve (1-50, default 5).
            category: Optional category ID (use get_trivia_categories to list them).
            difficulty: Optional difficulty — "easy", "medium", or "hard".

        Returns:
            A dict with response_code, response_message, and a list of decoded questions.
        """
        params: dict[str, str | int] = {"amount": amount}
        if category is not None:
            params["category"] = category
        if difficulty is not None:
            params["difficulty"] = difficulty

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(OPENTDB_API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        code = data.get("response_code", -1)
        if code != 0:
            return {
                "response_code": code,
                "response_message": RESPONSE_CODES.get(code, "Unknown error"),
                "questions": [],
            }

        questions = []
        for q in data.get("results", []):
            questions.append({
                "category": _decode(q["category"]),
                "type": q["type"],
                "difficulty": q["difficulty"],
                "question": _decode(q["question"]),
                "correct_answer": _decode(q["correct_answer"]),
                "incorrect_answers": [_decode(a) for a in q["incorrect_answers"]],
            })

        return {
            "response_code": code,
            "response_message": RESPONSE_CODES[code],
            "questions": questions,
        }

    @mcp.tool()
    async def list_trivia_categories() -> dict:
        """List all available trivia categories from the Open Trivia Database.

        Returns:
            A dict with a list of categories, each containing an id and name.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(OPENTDB_CATEGORIES_URL)
            resp.raise_for_status()
            data = resp.json()

        return {
            "categories": [
                {"id": c["id"], "name": _decode(c["name"])}
                for c in data.get("trivia_categories", [])
            ]
        }
