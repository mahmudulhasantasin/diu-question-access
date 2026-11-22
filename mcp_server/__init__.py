"""MCP Server package for DIU Question MCP."""

from mcp_server.tools import create_mcp_server
from mcp_server.resources import read_pdf_resource, read_collection_resource

__all__ = [
    "create_mcp_server",
    "read_pdf_resource",
    "read_collection_resource",
]
