"""MCP server for integrations providers."""

from mcp.server.fastmcp import FastMCP

from providers import register_all_providers

mcp = FastMCP("integrations-mcp")
register_all_providers(mcp)

if __name__ == "__main__":
    mcp.run()
