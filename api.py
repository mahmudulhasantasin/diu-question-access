"""Production-grade FastAPI REST & OpenAPI interface for DIU Question MCP Server.

Provides:
  - Standard REST API with OpenAPI 3.1 specifications (for ChatGPT Custom Actions, Web, and Mobile)
  - Interactive Swagger Documentation at /docs
  - Health check endpoint at /health (for Cloud platforms & Docker)
  - Direct binary PDF streaming at /api/files/{file_id}/download
  - MCP SSE Server mounted for remote MCP clients
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import List, Union, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from config import SERVER_NAME, SERVER_VERSION, LOG_LEVEL
from database.models import CollectionSummary
from services.collection_service import CollectionService
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


def create_app() -> FastAPI:
    """Create configured production FastAPI application."""
    service = CollectionService()
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

    # Enable CORS for all origins (required for web clients and ChatGPT Actions)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------------
    # Health Check (Kubernetes, Docker, Cloud Run, Render, Railway)
    # -------------------------------------------------------------
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
        meta = service.get_pdf_metadata(file_id)
        if not meta or not meta.local_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{file_id}' not found.")

        path = Path(meta.local_path)
        if not path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File on disk missing.")

        return FileResponse(
            path=path,
            media_type="application/pdf",
            filename=path.name,
            content_disposition_type="attachment",
        )

    @app.get("/api/collections/{collection_id}", tags=["Collected PDFs"])
    async def get_collection_summary(collection_id: str):
        """Get summary statistics for a collection bundle."""
        summary = service.get_collection_summary(collection_id)
        if not summary:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Collection '{collection_id}' not found.")
        return summary

    # -------------------------------------------------------------
    # Mount MCP SSE Application for Remote MCP Clients
    # -------------------------------------------------------------
    try:
        sse_app = mcp_app_instance.sse_app()
        app.mount("/mcp", sse_app)
        logger.info("Mounted MCP SSE App at /mcp")
    except Exception as e:
        logger.warning(f"Could not mount MCP SSE sub-app: {e}")

    return app


# Production WSGI/ASGI entrypoint: uvicorn api:app
app = create_app()
