"""DIU Question MCP Server & REST API entry point.

Modes:
  1. stdio (default): For local Claude Desktop, Cursor, VS Code.
  2. http: Runs the production-grade FastAPI REST API + OpenAPI 3.1 + MCP SSE server.
  3. sse: Runs the standalone MCP SSE server.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    SERVER_NAME, SERVER_VERSION, DEFAULT_TRANSPORT,
    SERVER_HOST, SERVER_PORT, LOG_LEVEL
)


def setup_logging(transport: str, log_level: str = "INFO"):
    """Configure structured logging. In stdio mode, logs go to stderr to preserve stdout JSON-RPC."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)


def main():
    parser = argparse.ArgumentParser(
        description=f"{SERVER_NAME} v{SERVER_VERSION} - DIU Previous Question MCP & REST Server"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse", "streamable-http"],
        default=DEFAULT_TRANSPORT,
        help="Transport / Execution mode (stdio, http, sse, streamable-http)",
    )
    parser.add_argument(
        "--host",
        default=SERVER_HOST,
        help="Host address for HTTP/SSE transport (default: 127.0.0.1 or 0.0.0.0 for Docker/Cloud)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=SERVER_PORT,
        help="Port number for HTTP/SSE transport (default: 8000)",
    )
    parser.add_argument(
        "--log-level",
        default=LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()
    setup_logging(args.transport, args.log_level)
    logger = logging.getLogger("diu_mcp.server")

    logger.info(f"Starting {SERVER_NAME} v{SERVER_VERSION} (mode: {args.transport})...")

    if args.transport == "http":
        import uvicorn
        logger.info(f"Serving Production REST API & MCP SSE on http://{args.host}:{args.port}")
        logger.info(f"Interactive Swagger Docs available at: http://{args.host}:{args.port}/docs")
        logger.info(f"OpenAPI Schema available at: http://{args.host}:{args.port}/openapi.json")
        uvicorn.run("api:app", host=args.host, port=args.port, reload=False)
    elif args.transport == "stdio":
        from mcp_server.tools import create_mcp_server
        app = create_mcp_server()
        app.run(transport="stdio")
    elif args.transport == "sse":
        from mcp_server.tools import create_mcp_server
        app = create_mcp_server()
        logger.info(f"Serving MCP SSE on http://{args.host}:{args.port}/sse")
        app.run(transport="sse", host=args.host, port=args.port)
    elif args.transport == "streamable-http":
        from mcp_server.tools import create_mcp_server
        app = create_mcp_server()
        logger.info(f"Serving MCP Streamable HTTP on http://{args.host}:{args.port}/mcp")
        app.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
