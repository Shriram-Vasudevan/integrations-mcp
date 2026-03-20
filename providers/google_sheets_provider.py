"""Google Sheets provider using google-api-python-client.

Authenticates via GOOGLE_SERVICE_ACCOUNT_JSON env var (JSON string of a
service-account key).  Exposes: list_spreadsheets, read_sheet, write_sheet,
append_rows, create_spreadsheet, get_sheet_metadata.
"""

import json
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

_cached_credentials = None


def _get_credentials():
    """Build and cache service-account credentials from env."""
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.oauth2.service_account import Credentials

    global _cached_credentials
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not sa_json:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON environment variable is required"
        )
    if _cached_credentials is None or not _cached_credentials.valid:
        info = json.loads(sa_json)
        _cached_credentials = Credentials.from_service_account_info(
            info, scopes=SHEETS_SCOPES
        )
    if _cached_credentials.expired:
        _cached_credentials.refresh(GoogleAuthRequest())
    return _cached_credentials


def _sheets_service():
    """Return a Google Sheets API v4 service client."""
    from googleapiclient.discovery import build

    return build("sheets", "v4", credentials=_get_credentials(), cache_discovery=False)


def _drive_service():
    """Return a Google Drive API v3 service client."""
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=_get_credentials(), cache_discovery=False)


def register(mcp: FastMCP) -> None:
    """Register Google Sheets tools with the MCP server."""

    @mcp.tool()
    def list_spreadsheets(
        page_size: int = 20,
        page_token: Optional[str] = None,
        query: Optional[str] = None,
    ) -> dict:
        """List Google Sheets spreadsheets accessible to the service account.

        Uses the Google Drive API to find spreadsheet files.

        Args:
            page_size: Maximum number of spreadsheets to return (1-100, default 20).
            page_token: Token for the next page of results (from a previous call).
            query: Optional extra Drive search query appended to the mime filter
                   (e.g. "name contains 'Budget'").

        Returns:
            List of spreadsheets with id, name, createdTime, modifiedTime, and
            a next_page_token for pagination.
        """
        q = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        if query:
            q += f" and ({query})"

        kwargs = {
            "q": q,
            "pageSize": min(max(1, page_size), 100),
            "fields": "nextPageToken,files(id,name,createdTime,modifiedTime,owners)",
            "orderBy": "modifiedTime desc",
        }
        if page_token:
            kwargs["pageToken"] = page_token

        result = _drive_service().files().list(**kwargs).execute()
        spreadsheets = []
        for f in result.get("files", []):
            owners = [o.get("emailAddress", "") for o in f.get("owners", [])]
            spreadsheets.append({
                "id": f["id"],
                "name": f.get("name", ""),
                "createdTime": f.get("createdTime", ""),
                "modifiedTime": f.get("modifiedTime", ""),
                "owners": owners,
            })
        return {
            "spreadsheets": spreadsheets,
            "next_page_token": result.get("nextPageToken", ""),
        }

    @mcp.tool()
    def read_sheet(
        spreadsheet_id: str,
        range: str,
        major_dimension: str = "ROWS",
        value_render_option: str = "FORMATTED_VALUE",
    ) -> dict:
        """Read values from a spreadsheet range.

        Args:
            spreadsheet_id: The ID of the spreadsheet (from the URL).
            range: Range in A1 notation (e.g. "Sheet1!A1:D10" or "A1:D10").
            major_dimension: "ROWS" (default) or "COLUMNS".
            value_render_option: "FORMATTED_VALUE" (default), "UNFORMATTED_VALUE",
                                 or "FORMULA".

        Returns:
            The resolved range and values as a list of lists.
        """
        result = (
            _sheets_service()
            .spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=range,
                majorDimension=major_dimension,
                valueRenderOption=value_render_option,
            )
            .execute()
        )
        return {
            "range": result.get("range", range),
            "majorDimension": result.get("majorDimension", major_dimension),
            "values": result.get("values", []),
        }

    @mcp.tool()
    def write_sheet(
        spreadsheet_id: str,
        range: str,
        values: list[list],
        value_input_option: str = "USER_ENTERED",
    ) -> dict:
        """Write values to a spreadsheet range (overwrites existing data).

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            range: Range in A1 notation (e.g. "Sheet1!A1:D10").
            values: List of rows, each row a list of cell values.
            value_input_option: "USER_ENTERED" (default, parses formulas) or "RAW".

        Returns:
            Update metadata: updatedRange, updatedRows, updatedColumns, updatedCells.
        """
        body = {
            "range": range,
            "majorDimension": "ROWS",
            "values": values,
        }
        result = (
            _sheets_service()
            .spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range,
                valueInputOption=value_input_option,
                body=body,
            )
            .execute()
        )
        return {
            "updatedRange": result.get("updatedRange", ""),
            "updatedRows": result.get("updatedRows", 0),
            "updatedColumns": result.get("updatedColumns", 0),
            "updatedCells": result.get("updatedCells", 0),
        }

    @mcp.tool()
    def append_rows(
        spreadsheet_id: str,
        range: str,
        values: list[list],
        value_input_option: str = "USER_ENTERED",
        insert_data_option: str = "INSERT_ROWS",
    ) -> dict:
        """Append rows after the last row of data in a range.

        Args:
            spreadsheet_id: The ID of the spreadsheet.
            range: A1 range indicating the table to append to (e.g. "Sheet1!A:D").
            values: List of rows to append, each row a list of cell values.
            value_input_option: "USER_ENTERED" (default) or "RAW".
            insert_data_option: "INSERT_ROWS" (default) or "OVERWRITE".

        Returns:
            Update metadata: updatedRange, updatedRows, updatedColumns, updatedCells.
        """
        body = {
            "majorDimension": "ROWS",
            "values": values,
        }
        result = (
            _sheets_service()
            .spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range,
                valueInputOption=value_input_option,
                insertDataOption=insert_data_option,
                body=body,
            )
            .execute()
        )
        updates = result.get("updates", {})
        return {
            "updatedRange": updates.get("updatedRange", ""),
            "updatedRows": updates.get("updatedRows", 0),
            "updatedColumns": updates.get("updatedColumns", 0),
            "updatedCells": updates.get("updatedCells", 0),
        }

    @mcp.tool()
    def create_spreadsheet(
        title: str,
        sheet_names: Optional[list[str]] = None,
    ) -> dict:
        """Create a new Google Sheets spreadsheet.

        Args:
            title: Title of the new spreadsheet.
            sheet_names: Optional list of sheet (tab) names to create.
                         Defaults to a single "Sheet1" if omitted.

        Returns:
            The new spreadsheet's id, title, url, and list of sheet names.
        """
        body: dict = {"properties": {"title": title}}
        if sheet_names:
            body["sheets"] = [
                {"properties": {"title": name}} for name in sheet_names
            ]
        result = (
            _sheets_service()
            .spreadsheets()
            .create(body=body)
            .execute()
        )
        sheets = [
            s.get("properties", {}).get("title", "")
            for s in result.get("sheets", [])
        ]
        return {
            "spreadsheetId": result.get("spreadsheetId", ""),
            "title": result.get("properties", {}).get("title", title),
            "spreadsheetUrl": result.get("spreadsheetUrl", ""),
            "sheets": sheets,
        }

    @mcp.tool()
    def get_sheet_metadata(spreadsheet_id: str) -> dict:
        """Get spreadsheet metadata including all sheet (tab) properties.

        Args:
            spreadsheet_id: The ID of the spreadsheet.

        Returns:
            Spreadsheet title, locale, and list of sheets with sheetId, title,
            index, rowCount, and columnCount.
        """
        result = (
            _sheets_service()
            .spreadsheets()
            .get(
                spreadsheetId=spreadsheet_id,
                fields="spreadsheetId,properties,sheets.properties",
            )
            .execute()
        )
        sheets = []
        for s in result.get("sheets", []):
            props = s.get("properties", {})
            grid = props.get("gridProperties", {})
            sheets.append({
                "sheetId": props.get("sheetId"),
                "title": props.get("title", ""),
                "index": props.get("index", 0),
                "rowCount": grid.get("rowCount", 0),
                "columnCount": grid.get("columnCount", 0),
            })
        return {
            "spreadsheetId": result.get("spreadsheetId", spreadsheet_id),
            "title": result.get("properties", {}).get("title", ""),
            "locale": result.get("properties", {}).get("locale", ""),
            "sheets": sheets,
        }
