"""Dictionary provider using the Free Dictionary API.

Exposes tools for word definitions, phonetics, part of speech, examples,
and synonym/antonym extraction.  No authentication required.
"""

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries"


async def _lookup(word: str, language: str = "en") -> list[dict]:
    """Fetch dictionary data for a word."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{BASE_URL}/{language}/{word}")
        if resp.status_code == 404:
            raise ValueError(f"Word not found: '{word}'")
        resp.raise_for_status()
        return resp.json()


def register(mcp: FastMCP) -> None:
    """Register dictionary tools with the MCP server."""

    @mcp.tool()
    async def define_word(word: str, language: str = "en") -> dict:
        """Look up the definition of a word.

        Returns phonetic transcription, parts of speech, definitions,
        example sentences, and synonyms when available.  Uses the Free
        Dictionary API (no authentication required).

        Args:
            word: The word to define.
            language: ISO 639-1 language code (default "en").
                Supported: en, hi, es, fr, ja, ru, de, it, ko, pt-BR, ar, tr.

        Returns:
            The word, its phonetic transcription, and meanings with
            definitions grouped by part of speech.
        """
        try:
            entries = await _lookup(word, language)
        except ValueError:
            return {
                "word": word,
                "error": "Word not found. Please check the spelling and try again.",
            }

        entry = entries[0]

        # Resolve phonetic: top-level field first, then phonetics list.
        phonetic = entry.get("phonetic", "")
        if not phonetic:
            for p in entry.get("phonetics", []):
                if p.get("text"):
                    phonetic = p["text"]
                    break

        # Collect audio URLs from phonetics.
        audio_urls = [
            p["audio"]
            for p in entry.get("phonetics", [])
            if p.get("audio")
        ]

        meanings: list[dict] = []
        for meaning in entry.get("meanings", []):
            part_of_speech = meaning.get("partOfSpeech", "unknown")
            defs: list[dict] = []
            syns: list[str] = list(meaning.get("synonyms", []))
            for d in meaning.get("definitions", []):
                item: dict = {"definition": d.get("definition", "")}
                if d.get("example"):
                    item["example"] = d["example"]
                syns.extend(d.get("synonyms", []))
                defs.append(item)
            syns = sorted(set(syns))
            if defs:
                entry_meaning: dict = {
                    "part_of_speech": part_of_speech,
                    "definitions": defs,
                }
                if syns:
                    entry_meaning["synonyms"] = syns
                meanings.append(entry_meaning)

        result: dict = {
            "word": entry.get("word", word),
            "phonetic": phonetic,
            "meanings": meanings,
        }
        if audio_urls:
            result["audio_urls"] = audio_urls
        return result

    @mcp.tool()
    async def get_synonyms(word: str, language: str = "en") -> dict:
        """Get synonyms and antonyms for a word.

        Extracts synonyms and antonyms from the Free Dictionary API response,
        grouped by part of speech.

        Args:
            word: The word to find synonyms and antonyms for.
            language: ISO 639-1 language code (default "en").

        Returns:
            Synonyms and antonyms grouped by part of speech.
        """
        try:
            entries = await _lookup(word, language)
        except ValueError:
            return {
                "word": word,
                "error": "Word not found. Please check the spelling and try again.",
            }

        results: list[dict] = []
        for entry in entries:
            for meaning in entry.get("meanings", []):
                # Collect synonyms from meaning level and definition level.
                syns: list[str] = list(meaning.get("synonyms", []))
                ants: list[str] = list(meaning.get("antonyms", []))
                for d in meaning.get("definitions", []):
                    syns.extend(d.get("synonyms", []))
                    ants.extend(d.get("antonyms", []))
                syns = sorted(set(syns))
                ants = sorted(set(ants))
                if syns or ants:
                    item: dict = {
                        "part_of_speech": meaning.get("partOfSpeech", "unknown"),
                    }
                    if syns:
                        item["synonyms"] = syns
                    if ants:
                        item["antonyms"] = ants
                    results.append(item)

        if not results:
            return {"word": word, "message": f"No synonyms or antonyms found for '{word}'."}

        return {"word": word, "results": results}
