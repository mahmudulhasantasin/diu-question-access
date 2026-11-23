"""Production-grade FastAPI REST & OpenAPI interface for DIU Question MCP Server.

Provides:
  - Standard REST API with OpenAPI 3.1 specifications (for ChatGPT Custom Actions, Web, and Mobile)
  - Interactive Swagger Documentation at /docs
  - Health check endpoint at /health (for Cloud platforms & Docker)
  - Direct binary PDF streaming at /api/files/{file_id}/download
  - MCP SSE Server mounted for remote MCP clients
"""

from contextlib import asynccontextmanager
import json
import logging
from pathlib import Path
from typing import List, Union, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from config import SERVER_NAME, SERVER_VERSION, LOG_LEVEL
from database.models import CollectionSummary
from services.collection_service import CollectionService
from services.preview_service import PreviewService
from mcp_server.tools import create_mcp_server

logger = logging.getLogger("diu_mcp.api")


# --- Request & Response Models for OpenAPI Documentation ---
class SearchRequest(BaseModel):
    department: str = Field(..., json_schema_extra={"example": "CSE"}, description="Department name or short code")
    course: str = Field(..., json_schema_extra={"example": "Operating Systems"}, description="Course name or code")
    semesters: Union[str, List[str]] = Field("all", json_schema_extra={"example": "Fall 26"}, description="Semester name(s) or 'all'")
    exam_types: Union[str, List[str]] = Field("all", json_schema_extra={"example": ["midterm", "quiz"]}, description="Exam type(s) or 'all'")


class CollectRequest(BaseModel):
    department: str = Field(..., json_schema_extra={"example": "CSE"}, description="Department name or short code")
    course: str = Field(..., json_schema_extra={"example": "Operating Systems"}, description="Course name or code")
    semesters: Union[str, List[str]] = Field("all", json_schema_extra={"example": "Fall 26"}, description="Semester name(s) or 'all'")
    exam_types: Union[str, List[str]] = Field("all", json_schema_extra={"example": ["midterm", "quiz"]}, description="Exam type(s) or 'all'")
    force_refresh: bool = Field(False, description="Re-download if already cached")


class HealthResponse(BaseModel):
    status: str
    version: str
    service: str
    database: str


class MCPProxyMiddleware:
    """Pure ASGI middleware to normalize paths and host headers for the MCP SSE sub-app.

    Avoids BaseHTTPMiddleware issues with streaming SSE, rewrites /mcp to /mcp/,
    and normalizes Host to localhost:8000 so FastMCP DNS rebinding allows cloud proxies (Render).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path", "").startswith("/mcp"):
            # Handle HEAD probes cleanly without opening an SSE stream
            if scope.get("method") == "HEAD":
                response = Response(status_code=200, media_type="text/event-stream")
                await response(scope, receive, send)
                return

            # For GET requests to /mcp, route to mounted SSE app at /mcp/
            if scope.get("method") == "GET" and scope.get("path") == "/mcp":
                scope["path"] = "/mcp/"

            headers = scope.get("headers", [])
            new_headers = []
            for k, v in headers:
                if k.lower() == b"host":
                    new_headers.append((b"host", b"localhost:8000"))
                elif k.lower() == b"origin":
                    continue
                else:
                    new_headers.append((k, v))
            scope["headers"] = new_headers
        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    """Create configured production FastAPI application."""
    service = CollectionService()
    preview_service = PreviewService(repo=service.repo)
    mcp_app_instance = create_mcp_server(service=service)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(f"Starting {SERVER_NAME} API v{SERVER_VERSION}...")
        # Pre-seed database connection
        service.repo.init_db()
        yield
        await service.client.close()
        logger.info(f"Shutting down {SERVER_NAME} API...")

    app = FastAPI(
        title="DIU Previous Question API & MCP Server",
        description=(
            "Production REST API and Model Context Protocol (MCP) server for dynamically "
            "discovering, collecting, and delivering original DIU examination question PDFs. "
            "Compatible with ChatGPT Custom Actions, Claude Desktop, Cursor, and any Cloud platform."
        ),
        version=SERVER_VERSION,
        lifespan=lifespan,
    )

    # Enable pure ASGI proxy middleware for MCP cloud compatibility
    app.add_middleware(MCPProxyMiddleware)

    # Enable CORS for all origins (required for web clients and ChatGPT Actions)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------------
    # Root & Health Check (Render, Cloud Run, Kubernetes, Docker)
    # -------------------------------------------------------------
    @app.get("/", tags=["Health"])
    @app.head("/", tags=["Health"])
    async def root():
        """Root endpoint returning service status and documentation links."""
        return {
            "status": "online",
            "service": SERVER_NAME,
            "version": SERVER_VERSION,
            "docs_url": "/docs",
            "openapi_url": "/openapi.json",
            "health_url": "/health",
            "mcp_url": "/mcp",
        }

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        """Health check endpoint for cloud monitoring and container orchestrators."""
        db_ok = service.repo.db_path.parent.exists()
        return HealthResponse(
            status="healthy" if db_ok else "degraded",
            version=SERVER_VERSION,
            service=SERVER_NAME,
            database="connected" if db_ok else "error",
        )

    # -------------------------------------------------------------
    # Streamable HTTP MCP JSON-RPC Handler (Gemini & modern MCP clients)
    # -------------------------------------------------------------
    @app.post("/mcp", tags=["MCP"])
    @app.post("/mcp/", tags=["MCP"])
    async def mcp_post_handler(request: Request):
        """Handle Streamable HTTP MCP JSON-RPC POST requests from Gemini and modern clients."""
        try:
            payload = await request.json()
        except Exception:
            return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}}, status_code=400)

        method = payload.get("method")
        req_id = payload.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": payload.get("params", {}).get("protocolVersion", "2024-11-05"),
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            }
        elif method == "tools/list":
            tools = await mcp_app_instance.list_tools()
            tools_list = []
            for t in tools:
                schema = getattr(t, "inputSchema", getattr(t, "parameters", None))
                if schema is None or not isinstance(schema, dict):
                    schema = {"type": "object", "properties": {}}
                tools_list.append({
                    "name": t.name,
                    "description": t.description or "",
                    "inputSchema": schema,
                })
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}
        elif method == "tools/call":
            params = payload.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            try:
                res = await mcp_app_instance.call_tool(name, args)
                items = []
                if hasattr(res, "content"):
                    items = res.content
                elif isinstance(res, (list, tuple)):
                    items = res
                elif res is not None:
                    items = [res]

                content = []
                for item in items:
                    if hasattr(item, "text"):
                        content.append({"type": "text", "text": item.text})
                    elif hasattr(item, "data"):
                        content.append({
                            "type": "image",
                            "data": getattr(item, "data", ""),
                            "mimeType": getattr(item, "mimeType", "image/png"),
                        })
                    elif isinstance(item, str):
                        content.append({"type": "text", "text": item})
                    elif isinstance(item, dict):
                        content.append({"type": "text", "text": json.dumps(item, indent=2)})
                    else:
                        content.append({"type": "text", "text": str(item)})

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": content, "isError": getattr(res, "is_error", False)},
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Error executing {name}: {e}"}], "isError": True},
                }
        elif method in ("resources/list", "prompts/list", "ping"):
            key = "resources" if "resources" in method else ("prompts" if "prompts" in method else None)
            res = {key: []} if key else {}
            return {"jsonrpc": "2.0", "id": req_id, "result": res}
        elif method == "notifications/initialized":
            return Response(status_code=status.HTTP_200_OK)

        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method '{method}' not found"}}

    # -------------------------------------------------------------
    # REST Endpoints for ChatGPT Actions and Web Clients
    # -------------------------------------------------------------
    @app.get("/api/departments", tags=["Discovery"])
    async def list_departments(force_refresh: bool = False):
        """List all academic departments discovered dynamically from OurDIU."""
        return await service.list_departments(force_refresh=force_refresh)

    @app.get("/api/courses", tags=["Discovery"])
    async def list_courses(
        department: str = Query(..., description="Department name or short code, e.g. 'CSE'"),
        force_refresh: bool = False,
    ):
        """List courses under the specified department."""
        try:
            return await service.list_courses(department, force_refresh=force_refresh)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @app.get("/api/semesters", tags=["Discovery"])
    async def list_semesters(
        department: str = Query(..., description="Department name or code, e.g. 'CSE'"),
        course: str = Query(..., description="Course name or code, e.g. 'Operating Systems'"),
    ):
        """List available semesters containing question papers for a specific course."""
        try:
            return await service.list_semesters(department, course)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @app.get("/api/exam-types", tags=["Discovery"])
    async def list_exam_types(
        department: str = Query(..., description="Department name or code, e.g. 'CSE'"),
        course: str = Query(..., description="Course name or code, e.g. 'Operating Systems'"),
    ):
        """List available exam categories (Midterm, Final, Quiz) for a specific course."""
        try:
            return await service.list_exam_types(department, course)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @app.post("/api/search", tags=["Examination Questions"])
    async def search_questions(req: SearchRequest):
        """Search matching exam entries and PDF URLs without downloading (Preview Mode)."""
        try:
            return await service.search_questions(
                department=req.department,
                course=req.course,
                semesters=req.semesters,
                exam_types=req.exam_types,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @app.post("/api/collect", response_model=CollectionSummary, tags=["Examination Questions"])
    async def collect_questions(req: CollectRequest):
        """Download all matching original PDFs, validate binary integrity, and return summary."""
        try:
            summary = await service.collect_questions(
                department=req.department,
                course=req.course,
                semesters=req.semesters,
                exam_types=req.exam_types,
                force_refresh=req.force_refresh,
            )
            return summary
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @app.get("/api/files", tags=["Collected PDFs"])
    async def list_files(bundle_id: Optional[str] = Query(None, description="Optional bundle/collection ID")):
        """List metadata and identifiers for downloaded PDF files."""
        return service.list_collected_files(bundle_id=bundle_id)

    @app.get("/api/files/{file_id}", tags=["Collected PDFs"])
    async def get_file_metadata(file_id: str):
        """Get complete metadata, question transcription, and download URL for a file."""
        meta = service.get_pdf_metadata(file_id)
        if not meta:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{file_id}' not found.")
        d = meta.to_dict()
        d["stream_url"] = f"/api/files/{file_id}/download"
        return d

    @app.get("/api/files/{file_id}/download", tags=["Collected PDFs"])
    async def download_file_binary(file_id: str):
        """Download or stream the original binary PDF document."""
        import httpx
        meta = service.get_pdf_metadata(file_id)
        if not meta:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{file_id}' not found.")

        # 1. If cached on local disk, serve directly
        if meta.local_path and Path(meta.local_path).is_file():
            path = Path(meta.local_path)
            return FileResponse(
                path=path,
                media_type="application/pdf",
                filename=path.name,
                content_disposition_type="attachment",
            )

        # 2. Otherwise stream on-the-fly from OurDIU with 0 permanent disk space
        if meta.pdf_url:
            async def stream_remote():
                async with httpx.AsyncClient(
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=httpx.Timeout(30.0),
                    follow_redirects=True,
                ) as client:
                    async with client.stream("GET", meta.pdf_url) as resp:
                        if resp.status_code != 200:
                            raise HTTPException(status_code=resp.status_code, detail="Remote PDF source unavailable.")
                        async for chunk in resp.aiter_bytes():
                            yield chunk

            filename = f"{meta.file_id}.pdf"
            return StreamingResponse(
                stream_remote(),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF binary source unavailable.")

    @app.get("/api/files/{file_id}/pages/{page_number}", tags=["Collected PDFs"])
    async def get_question_page_image(
        file_id: str,
        page_number: int = 1,
        scale: float = Query(2.0, ge=0.5, le=4.0, description="Image rendering scale / DPI multiplier"),
    ):
        """Render a specific page of an exam question PDF as a PNG image on-the-fly.
        
        Allows multi-modal LLMs (ChatGPT Vision, Claude) and web browsers to visually
        inspect diagrams, circuits, graphs, tables, and handwritten questions with zero
        permanent storage consumption.
        """
        try:
            png_bytes, p_num, total_pages = await preview_service.get_page_png_bytes(
                file_id=file_id,
                page_number=page_number,
                scale=scale,
            )
            return Response(
                content=png_bytes,
                media_type="image/png",
                headers={
                    "X-Total-Pages": str(total_pages),
                    "X-Current-Page": str(p_num),
                    "Cache-Control": "public, max-age=3600",
                },
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
        except Exception as err:
            logger.error(f"Error serving page preview image for {file_id}: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Rendering failed.")

    @app.get("/api/collections/{collection_id}", tags=["Collected PDFs"])
    async def get_collection_summary(collection_id: str):
        """Get summary statistics for a collection bundle."""
        summary = service.get_collection_summary(collection_id)
        if not summary:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Collection '{collection_id}' not found.")
        return summary

    # -------------------------------------------------------------
    # Mount MCP SSE Application for Remote MCP Clients (ChatGPT, Claude, Cursor)
    # -------------------------------------------------------------
    try:
        import inspect
        from starlette.routing import Route

        sig = inspect.signature(mcp_app_instance.sse_app)
        kwargs = {}
        if "transport_security" in sig.parameters:
            try:
                from mcp.server.transport_security import TransportSecuritySettings
                kwargs["transport_security"] = TransportSecuritySettings(enable_dns_rebinding_protection=False)
            except Exception:
                pass
        if "sse_path" in sig.parameters:
            kwargs["sse_path"] = "/"

        sse_app = mcp_app_instance.sse_app(**kwargs)

        # Ensure both / and /sse routes exist inside sse_app
        sse_endpoint = None
        for r in sse_app.routes:
            if getattr(r, "path", "") in ("/", "/sse"):
                sse_endpoint = r.endpoint
                break

        if sse_endpoint:
            existing_paths = [getattr(r, "path", "") for r in sse_app.routes]
            if "/" not in existing_paths:
                sse_app.routes.append(Route("/", endpoint=sse_endpoint, methods=["GET", "HEAD"]))
            if "/sse" not in existing_paths:
                sse_app.routes.append(Route("/sse", endpoint=sse_endpoint, methods=["GET", "HEAD"]))

        app.mount("/mcp", sse_app)
        logger.info("Mounted MCP SSE App at /mcp (supporting / and /sse)")
    except Exception as e:
        logger.warning(f"Could not mount MCP SSE sub-app: {e}")

    return app


# Production WSGI/ASGI entrypoint: uvicorn api:app
app = create_app()
