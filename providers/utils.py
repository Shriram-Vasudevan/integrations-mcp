"""UUID, hash, and encoding utilities provider — pure stdlib, no external APIs."""

import base64
import hashlib
import re
import secrets
import string
import uuid
from urllib.parse import quote, unquote, urlparse

from mcp.server.fastmcp import FastMCP

# Nanoid-style alphabet (URL-safe, no look-alikes)
_NANOID_ALPHABET = string.ascii_letters + string.digits + "-_"


def register(mcp: FastMCP) -> None:
    """Register utility tools with the MCP server."""

    @mcp.tool()
    async def generate_uuid(version: int = 4) -> dict:
        """Generate a UUID.

        Args:
            version: UUID version to generate (1 or 4). Default is 4.

        Returns:
            The generated UUID string and its version.
        """
        if version == 4:
            result = uuid.uuid4()
        elif version == 1:
            result = uuid.uuid1()
        else:
            return {"error": True, "message": f"Unsupported UUID version: {version}. Use 1 or 4."}
        return {"uuid": str(result), "version": version}

    @mcp.tool()
    async def generate_nanoid(size: int = 21) -> dict:
        """Generate a nanoid-style random ID using a URL-safe alphabet.

        Args:
            size: Length of the generated ID. Default is 21.

        Returns:
            The generated nanoid string.
        """
        if size < 1 or size > 256:
            return {"error": True, "message": "Size must be between 1 and 256."}
        nanoid = "".join(secrets.choice(_NANOID_ALPHABET) for _ in range(size))
        return {"nanoid": nanoid, "size": size}

    @mcp.tool()
    async def hash_text(text: str, algorithm: str = "sha256") -> dict:
        """Hash text using a specified algorithm.

        Args:
            text: The text to hash.
            algorithm: Hash algorithm — sha256, sha512, sha1, md5, sha384, sha224.
                       Default is sha256.

        Returns:
            The hex-encoded hash digest, algorithm used, and input length.
        """
        algo = algorithm.lower().strip()
        supported = {"sha256", "sha512", "sha1", "md5", "sha384", "sha224"}
        if algo not in supported:
            return {"error": True, "message": f"Unsupported algorithm: {algorithm}. Use one of: {', '.join(sorted(supported))}"}
        h = hashlib.new(algo)
        h.update(text.encode("utf-8"))
        return {"hash": h.hexdigest(), "algorithm": algo, "input_length": len(text)}

    @mcp.tool()
    async def encode_base64(text: str) -> dict:
        """Encode text to Base64.

        Args:
            text: The text to encode.

        Returns:
            The Base64-encoded string.
        """
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        return {"encoded": encoded, "input_length": len(text)}

    @mcp.tool()
    async def decode_base64(encoded: str) -> dict:
        """Decode a Base64 string back to text.

        Args:
            encoded: The Base64-encoded string to decode.

        Returns:
            The decoded text.
        """
        try:
            decoded = base64.b64decode(encoded).decode("utf-8")
        except Exception as exc:
            return {"error": True, "message": f"Failed to decode Base64: {exc}"}
        return {"decoded": decoded, "encoded_length": len(encoded)}

    @mcp.tool()
    async def url_encode(text: str) -> dict:
        """Percent-encode text for use in URLs.

        Args:
            text: The text to encode.

        Returns:
            The URL-encoded string.
        """
        encoded = quote(text)
        return {"encoded": encoded, "input_length": len(text)}

    @mcp.tool()
    async def url_decode(encoded: str) -> dict:
        """Decode a percent-encoded URL string.

        Args:
            encoded: The URL-encoded string to decode.

        Returns:
            The decoded text.
        """
        decoded = unquote(encoded)
        return {"decoded": decoded, "encoded_length": len(encoded)}

    @mcp.tool()
    async def generate_password(length: int = 16, include_symbols: bool = True) -> dict:
        """Generate a cryptographically secure random password.

        Args:
            length: Password length (8–128). Default is 16.
            include_symbols: Whether to include symbols (!@#$%^&*). Default is True.

        Returns:
            The generated password and its character composition.
        """
        if length < 8 or length > 128:
            return {"error": True, "message": "Length must be between 8 and 128."}

        alphabet = string.ascii_letters + string.digits
        if include_symbols:
            alphabet += "!@#$%^&*"

        # Guarantee at least one of each required class
        required: list[str] = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
        ]
        if include_symbols:
            required.append(secrets.choice("!@#$%^&*"))

        remaining = [secrets.choice(alphabet) for _ in range(length - len(required))]
        pool = required + remaining
        # Shuffle to avoid predictable positions
        password_chars = list(pool)
        secrets.SystemRandom().shuffle(password_chars)
        password = "".join(password_chars)

        return {
            "password": password,
            "length": length,
            "includes_symbols": include_symbols,
        }

    @mcp.tool()
    async def validate_email(email: str) -> dict:
        """Validate an email address format using a standard regex.

        Args:
            email: The email address to validate.

        Returns:
            Whether the email is valid, along with parsed local and domain parts.
        """
        pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
        is_valid = bool(re.match(pattern, email))
        result: dict = {"email": email, "valid": is_valid}
        if is_valid:
            local, domain = email.rsplit("@", 1)
            result["local"] = local
            result["domain"] = domain
        return result

    @mcp.tool()
    async def validate_url(url: str) -> dict:
        """Validate a URL and parse its components.

        Args:
            url: The URL to validate.

        Returns:
            Whether the URL is valid and its parsed components (scheme, host, path, etc.).
        """
        try:
            parsed = urlparse(url)
            is_valid = bool(parsed.scheme in ("http", "https") and parsed.netloc)
        except Exception:
            is_valid = False
            parsed = None

        result: dict = {"url": url, "valid": is_valid}
        if is_valid and parsed:
            result["scheme"] = parsed.scheme
            result["host"] = parsed.hostname
            result["port"] = parsed.port
            result["path"] = parsed.path
            result["query"] = parsed.query
            result["fragment"] = parsed.fragment
        return result
