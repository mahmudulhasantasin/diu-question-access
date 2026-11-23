"""MCP tools and resources registration for DIU Question MCP Server."""

import base64
import json
import logging
from typing import List, Union, Optional, Dict, Any
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer
    except ImportError:
        from mcp.server import Server as MCPServer
import mcp.types as types
from config import SERVER_NAME
from services.collection_service import CollectionService
from services.preview_service import PreviewService
from mcp_server.resources import read_pdf_resource, read_collection_resource

logger = logging.getLogger("diu_mcp.mcp_server.tools")


def create_mcp_server(service: Optional[CollectionService] = None) -> MCPServer:
    """Create and configure the MCPServer with all tools and resources."""
    app = MCPServer(SERVER_NAME)
    svc = service or CollectionService()
    preview_svc = PreviewService(repo=svc.repo)

    # -------------------------------------------------------------
    # Tool 1: list_departments
    # -------------------------------------------------------------
    @app.tool(
        name="list_departments",
        description=(
            "Discover and list all academic departments available in the DIU Question Bank "
            "(e.g. CSE, EEE, BBA, Agricultural Science, English). Call this first when the user "
            "asks for previous questions."
        ),
    )
    async def list_departments(force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Returns all available departments from OurDIU."""
        return await svc.list_departments(force_refresh=force_refresh)

    # -------------------------------------------------------------
    # Tool 2: list_courses
    # -------------------------------------------------------------
    @app.tool(
        name="list_courses",
        description=(
            "List all courses associated with a selected department. "
            "Use this to find the exact course name or code (e.g. 'Operating Systems', 'Algorithms', 'Data Structures') "
            "after the user selects a department."
        ),
    )
    async def list_courses(
        department: str,
        force_refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """Returns courses associated with the selected department."""
        return await svc.list_courses(department, force_refresh=force_refresh)

    # -------------------------------------------------------------
    # Tool 3: list_semesters
    # -------------------------------------------------------------
    @app.tool(
        name="list_semesters",
        description=(
            "List all academic semesters available for a specific course in a department "
            "(e.g. 'Fall 24', 'Spring 25', 'Summer 24'). Default option for users is 'all'."
        ),
    )
    async def list_semesters(
        department: str,
        course: str,
    ) -> List[Dict[str, Any]]:
        """Returns available semesters for the selected course."""
        return await svc.list_semesters(department, course)

    # -------------------------------------------------------------
    # Tool 4: list_exam_types
    # -------------------------------------------------------------
    @app.tool(
        name="list_exam_types",
        description=(
            "List available exam types for a specific course (e.g. Midterm, Final, Quiz). "
            "Users may select one, multiple, or 'all'."
        ),
    )
    async def list_exam_types(
        department: str,
        course: str,
    ) -> List[Dict[str, Any]]:
        """Returns available exam types for the selected course."""
        return await svc.list_exam_types(department, course)

    # -------------------------------------------------------------
    # Tool 5: search_questions
    # -------------------------------------------------------------
    @app.tool(
        name="search_questions",
        description=(
            "Finds all matching examination records and their original PDF URLs without downloading. "
            "Useful for previewing available question papers before initiating download."
        ),
    )
    async def search_questions(
        department: str,
        course: str,
        semesters: Union[str, List[str]] = "all",
        exam_types: Union[str, List[str]] = "all",
    ) -> Dict[str, Any]:
        """Finds all matching exam entries and their original PDF URLs."""
        return await svc.search_questions(
            department=department,
            course=course,
            semesters=semesters,
            exam_types=exam_types,
        )

    # -------------------------------------------------------------
    # Tool 6: collect_questions
    # -------------------------------------------------------------
    @app.tool(
        name="collect_questions",
        description=(
            "Downloads all matching original question paper PDFs from OurDIU. "
            "Preserves original PDF binary without modification or OCR. "
            "Defaults to all semesters if not specified. Supports single or multiple semesters and exam types."
        ),
    )
    async def collect_questions(
        department: str,
        course: str,
        semesters: Union[str, List[str]] = "all",
        exam_types: Union[str, List[str]] = "all",
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Downloads all matching original PDFs and returns a collection summary."""
        summary = await svc.collect_questions(
            department=department,
            course=course,
            semesters=semesters,
            exam_types=exam_types,
            force_refresh=force_refresh,
        )
        return summary.model_dump()

    # -------------------------------------------------------------
    # Tool 7: list_collected_files
    # -------------------------------------------------------------
    @app.tool(
        name="list_collected_files",
        description=(
            "Returns metadata, file IDs, file sizes, and local paths for all downloaded PDFs. "
            "Can filter by bundle_id from collect_questions."
        ),
    )
    async def list_collected_files(
        bundle_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Returns metadata and identifiers for all downloaded PDFs."""
        return svc.list_collected_files(bundle_id=bundle_id)

    # -------------------------------------------------------------
    # Tool 8: get_pdf_file
    # -------------------------------------------------------------
    @app.tool(
        name="get_pdf_file",
        description=(
            "Retrieves an individual original PDF file by its file_id. "
            "Returns binary PDF content as an embedded MCP Blob resource (MIME: application/pdf) "
            "along with local file path and SHA-256 checksum for AI document analysis."
        ),
    )
    async def get_pdf_file(
        file_id: str,
    ) -> List[Union[types.TextContent, types.EmbeddedResource]]:
        """Returns one individual original PDF through an MCP-compatible resource or file-delivery mechanism."""
        meta = svc.get_pdf_metadata(file_id)
        if not meta:
            raise ValueError(f"File ID '{file_id}' not found.")

        meta_info = {
            "file_id": meta.file_id,
            "department": meta.department_short,
            "course": meta.course_name,
            "semester": meta.semester,
            "exam_type": meta.exam_type,
            "section": meta.section,
            "batch": meta.batch,
            "file_size_bytes": meta.file_size,
            "sha256": meta.sha256,
            "local_path": meta.local_path,
            "pdf_download_url": meta.pdf_url,
            "pdf_resource_uri": f"diu-question://pdf/{file_id}",
            "mime_type": "application/pdf",
            "question_text": meta.question_text or "Question text not available in website transcription. Please refer to original PDF.",
            "message": (
                "Original examination question paper retrieved successfully. "
                "The full official question transcription is provided in 'question_text'. "
                "The original binary PDF is saved locally at 'local_path' and directly accessible via 'pdf_download_url'."
            )
        }

        content_blocks: List[Union[types.TextContent, types.EmbeddedResource]] = [
            types.TextContent(type="text", text=json.dumps(meta_info, indent=2))
        ]

        # Attach EmbeddedResource if within safe client buffer limits (< 250 KB)
        if meta.file_size <= 250_000:
            try:
                blob_resource = read_pdf_resource(svc, file_id)
                content_blocks.append(types.EmbeddedResource(type="resource", resource=blob_resource))
            except Exception as e:
                logger.warning(f"Could not attach binary resource for {file_id}: {e}")

        return content_blocks

    # -------------------------------------------------------------
    # Tool 9: get_question_collection_summary
    # -------------------------------------------------------------
    @app.tool(
        name="get_question_collection_summary",
        description=(
            "Returns a structured summary of a collection session by collection_id: "
            "total exams found, total PDFs collected, semester distribution, exam type distribution, "
            "file sizes, and any download failures."
        ),
    )
    async def get_question_collection_summary(
        collection_id: str,
    ) -> Dict[str, Any]:
        """Returns structured summary for a collection session."""
        summary = svc.get_collection_summary(collection_id)
        if not summary:
            raise ValueError(f"Collection ID '{collection_id}' not found.")
        return summary

    # -------------------------------------------------------------
    # Tool 10: preview_question_page
    # -------------------------------------------------------------
    @app.tool(
        name="preview_question_page",
        description=(
            "Render an original question paper page as a high-resolution PNG image. "
            "Essential for multimodal AI models (Claude, ChatGPT, Cursor) to visually inspect "
            "diagrams, circuits, flowcharts, graphs, mathematical equations, and handwritten exam sheets. "
            "Works completely in-memory without wasting disk space."
        ),
    )
    async def preview_question_page(
        file_id: str,
        page_number: int = 1,
    ) -> List[Union[types.TextContent, types.ImageContent]]:
        """Renders page as PNG image and returns both metadata and ImageContent."""
        png_bytes, p_num, total_pages = await preview_svc.get_page_png_bytes(
            file_id=file_id, page_number=page_number, scale=2.0
        )
        base64_data = base64.b64encode(png_bytes).decode("ascii")

        meta = svc.get_pdf_metadata(file_id)
        course_label = meta.course_name if meta else file_id
        sem_label = f" ({meta.semester} {meta.exam_type})" if meta else ""
        caption = f"Page {p_num} of {total_pages} for {course_label}{sem_label}"

        return [
            types.TextContent(
                type="text",
                text=json.dumps({
                    "file_id": file_id,
                    "page_number": p_num,
                    "total_pages": total_pages,
                    "caption": caption,
                    "image_format": "image/png",
                    "resolution": "High-DPI (scale 2.0)",
                    "message": "Question page rendered successfully. Visual diagram/image attached below."
                }, indent=2)
            ),
            types.ImageContent(
                type="image",
                data=base64_data,
                mimeType="image/png"
            )
        ]

    # -------------------------------------------------------------
    # Resource: diu-question://pdf/{file_id}
    # -------------------------------------------------------------
    @app.resource(
        "diu-question://pdf/{file_id}",
        name="Original Question PDF",
        description="Binary original exam question PDF (application/pdf)",
        mime_type="application/pdf",
    )
    async def pdf_resource(file_id: str) -> types.BlobResourceContents:
        return read_pdf_resource(svc, file_id)

    # -------------------------------------------------------------
    # Resource: diu-question://collection/{collection_id}
    # -------------------------------------------------------------
    @app.resource(
        "diu-question://collection/{collection_id}",
        name="Collection Manifest",
        description="Collection metadata manifest JSON",
        mime_type="application/json",
    )
    async def collection_resource(collection_id: str) -> types.TextResourceContents:
        return read_collection_resource(svc, collection_id)

    return app
