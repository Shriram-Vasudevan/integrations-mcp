"""AWS S3 provider wrapping the S3 API via boto3."""

import json
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

MAX_READ_SIZE = 1 * 1024 * 1024  # 1 MB


def _get_client():
    """Return a boto3 S3 client using standard AWS env vars."""
    import boto3
    return boto3.client("s3")


def register(mcp: FastMCP) -> None:
    """Register AWS S3 tools with the MCP server."""

    @mcp.tool()
    def s3_list_buckets() -> dict:
        """List all S3 buckets in the AWS account.

        Returns:
            List of buckets with name and creation date.
        """
        client = _get_client()
        resp = client.list_buckets()
        buckets = []
        for b in resp.get("Buckets", []):
            buckets.append({
                "name": b["Name"],
                "creation_date": b["CreationDate"].isoformat(),
            })
        return {"buckets": buckets, "owner": resp.get("Owner", {}).get("DisplayName")}

    @mcp.tool()
    def s3_list_objects(
        bucket: str,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: int = 100,
        continuation_token: Optional[str] = None,
    ) -> dict:
        """List objects in an S3 bucket with optional prefix and delimiter.

        Args:
            bucket: The S3 bucket name.
            prefix: Filter results to keys starting with this prefix (optional).
            delimiter: Delimiter for grouping keys, e.g. "/" for folder-like listing (optional).
            max_keys: Maximum number of keys to return (default 100, max 1000).
            continuation_token: Token for paginating through results (optional).

        Returns:
            List of objects with key, size, and last modified date, plus common prefixes if delimiter is used.
        """
        client = _get_client()
        params = {"Bucket": bucket, "MaxKeys": min(max_keys, 1000)}
        if prefix:
            params["Prefix"] = prefix
        if delimiter:
            params["Delimiter"] = delimiter
        if continuation_token:
            params["ContinuationToken"] = continuation_token

        resp = client.list_objects_v2(**params)

        objects = []
        for obj in resp.get("Contents", []):
            objects.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
                "storage_class": obj.get("StorageClass"),
            })

        common_prefixes = [cp["Prefix"] for cp in resp.get("CommonPrefixes", [])]

        result = {
            "objects": objects,
            "key_count": resp.get("KeyCount", 0),
            "is_truncated": resp.get("IsTruncated", False),
        }
        if common_prefixes:
            result["common_prefixes"] = common_prefixes
        if resp.get("NextContinuationToken"):
            result["next_continuation_token"] = resp["NextContinuationToken"]
        return result

    @mcp.tool()
    def s3_get_object_metadata(bucket: str, key: str) -> dict:
        """Get metadata for an S3 object (HEAD request).

        Args:
            bucket: The S3 bucket name.
            key: The object key.

        Returns:
            Object metadata including size, content type, last modified, and ETag.
        """
        client = _get_client()
        resp = client.head_object(Bucket=bucket, Key=key)
        return {
            "bucket": bucket,
            "key": key,
            "content_length": resp["ContentLength"],
            "content_type": resp.get("ContentType"),
            "last_modified": resp["LastModified"].isoformat(),
            "etag": resp.get("ETag"),
            "storage_class": resp.get("StorageClass"),
            "metadata": resp.get("Metadata", {}),
        }

    @mcp.tool()
    def s3_read_object(bucket: str, key: str) -> dict:
        """Read the content of a small text or JSON object from S3.

        Only reads objects up to 1 MB. For larger objects, use generate_presigned_url.

        Args:
            bucket: The S3 bucket name.
            key: The object key.

        Returns:
            The object content as text, plus metadata.
        """
        client = _get_client()
        # Check size first
        head = client.head_object(Bucket=bucket, Key=key)
        size = head["ContentLength"]
        if size > MAX_READ_SIZE:
            return {
                "error": f"Object is {size} bytes ({size / 1024 / 1024:.2f} MB), exceeding the 1 MB limit. Use s3_generate_presigned_url to get a download link instead.",
                "bucket": bucket,
                "key": key,
                "content_length": size,
            }

        resp = client.get_object(Bucket=bucket, Key=key)
        body = resp["Body"].read()

        content_type = resp.get("ContentType", "")
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            return {
                "error": "Object contains binary data that cannot be displayed as text. Use s3_generate_presigned_url to download it.",
                "bucket": bucket,
                "key": key,
                "content_type": content_type,
                "content_length": size,
            }

        # Try to parse as JSON for nicer output
        if "json" in content_type or key.endswith(".json"):
            try:
                text = json.loads(text)
                return {
                    "bucket": bucket,
                    "key": key,
                    "content_type": content_type,
                    "content_length": size,
                    "content": text,
                }
            except json.JSONDecodeError:
                pass

        return {
            "bucket": bucket,
            "key": key,
            "content_type": content_type,
            "content_length": size,
            "content": text,
        }

    @mcp.tool()
    def s3_put_object(
        bucket: str,
        key: str,
        content: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Upload text or JSON content to an S3 object.

        Args:
            bucket: The S3 bucket name.
            key: The object key (path).
            content: The text or JSON string content to upload.
            content_type: MIME type (default: auto-detected from key extension, falls back to text/plain).
            metadata: Custom metadata key-value pairs to attach to the object (optional).

        Returns:
            Upload confirmation with ETag and version ID.
        """
        client = _get_client()
        params = {
            "Bucket": bucket,
            "Key": key,
            "Body": content.encode("utf-8"),
        }

        if content_type:
            params["ContentType"] = content_type
        elif key.endswith(".json"):
            params["ContentType"] = "application/json"
        elif key.endswith(".html"):
            params["ContentType"] = "text/html"
        elif key.endswith(".csv"):
            params["ContentType"] = "text/csv"
        else:
            params["ContentType"] = "text/plain"

        if metadata:
            params["Metadata"] = metadata

        resp = client.put_object(**params)
        return {
            "bucket": bucket,
            "key": key,
            "etag": resp.get("ETag"),
            "version_id": resp.get("VersionId"),
        }

    @mcp.tool()
    def s3_delete_object(bucket: str, key: str) -> dict:
        """Delete an object from S3.

        Args:
            bucket: The S3 bucket name.
            key: The object key to delete.

        Returns:
            Deletion confirmation with version ID and delete marker info.
        """
        client = _get_client()
        resp = client.delete_object(Bucket=bucket, Key=key)
        return {
            "bucket": bucket,
            "key": key,
            "delete_marker": resp.get("DeleteMarker", False),
            "version_id": resp.get("VersionId"),
        }

    @mcp.tool()
    def s3_copy_object(
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
    ) -> dict:
        """Copy an object from one S3 location to another.

        Args:
            source_bucket: The source bucket name.
            source_key: The source object key.
            dest_bucket: The destination bucket name.
            dest_key: The destination object key.

        Returns:
            Copy confirmation with ETag and version ID.
        """
        client = _get_client()
        resp = client.copy_object(
            CopySource={"Bucket": source_bucket, "Key": source_key},
            Bucket=dest_bucket,
            Key=dest_key,
        )
        copy_result = resp.get("CopyObjectResult", {})
        return {
            "source": f"s3://{source_bucket}/{source_key}",
            "destination": f"s3://{dest_bucket}/{dest_key}",
            "etag": copy_result.get("ETag"),
            "last_modified": copy_result.get("LastModified").isoformat() if copy_result.get("LastModified") else None,
            "version_id": resp.get("VersionId"),
        }

    @mcp.tool()
    def s3_generate_presigned_url(
        bucket: str,
        key: str,
        expiry_seconds: int = 3600,
        http_method: str = "GET",
    ) -> dict:
        """Generate a presigned URL for temporary access to an S3 object.

        Args:
            bucket: The S3 bucket name.
            key: The object key.
            expiry_seconds: URL expiry time in seconds (default 3600 = 1 hour).
            http_method: HTTP method for the URL: GET or PUT (default GET).

        Returns:
            The presigned URL and its expiry time.
        """
        client = _get_client()
        client_method = "get_object" if http_method.upper() == "GET" else "put_object"
        url = client.generate_presigned_url(
            ClientMethod=client_method,
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry_seconds,
        )
        return {
            "bucket": bucket,
            "key": key,
            "url": url,
            "http_method": http_method.upper(),
            "expires_in_seconds": expiry_seconds,
        }
