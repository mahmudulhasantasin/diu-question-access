"""Unit tests for MCP server tool registration, invocation, and PDF resource delivery."""

import pytest
from pathlib import Path
from database.models import Department, Course, Semester, ExamType, ExamRecord, PDFMetadata
from database.repository import DatabaseRepository
from downloader.storage import PDFStorageManager
from downloader.pdf_downloader import PDFDownloader
from services.collection_service import CollectionService
from mcp_server.tools import create_mcp_server
from mcp_server.resources import read_pdf_resource, read_collection_resource
import mcp.types as types


@pytest.fixture
def mock_env(tmp_path):
    db_file = tmp_path / "test.db"
    repo = DatabaseRepository(db_path=db_file)
    storage = PDFStorageManager(base_dir=tmp_path / "data")
    downloader = PDFDownloader(storage_manager=storage)

    # Seed mock data
    repo.upsert_departments([
        Department(id=5, name="Computer Science and Engineering", short_name="CSE", published_count=730),
        Department(id=7, name="Electrical and Electronic Engineering", short_name="EEE", published_count=150),
    ])

    repo.upsert_courses([
        Course(id=227, name="Operating Systems", department_id=5, published_count=14, aliases=["os"]),
        Course(id=85, name="Data Structures", department_id=5, published_count=37, aliases=["ds"]),
    ])

    repo.upsert_semesters([
        Semester(id=20, name="Fall 26"),
        Semester(id=10, name="Fall 24"),
    ])

    repo.upsert_exam_types([
        ExamType(id=4, name="Midterm", normalized="midterm"),
        ExamType(id=1, name="Final", normalized="final"),
    ])

    service = CollectionService(repo=repo, downloader=downloader)
    app = create_mcp_server(service=service)
    return {"repo": repo, "service": service, "app": app, "storage": storage, "tmp_path": tmp_path}


def test_mcp_tools_registration(mock_env):
    app = mock_env["app"]
    # FastMCP/MCPServer stores tools in its list_tools or call_tool
    assert app is not None
    # Verify tool decorator added all 9 tools
    expected_tools = [
        "list_departments",
        "list_courses",
        "list_semesters",
        "list_exam_types",
        "search_questions",
        "collect_questions",
        "list_collected_files",
        "get_pdf_file",
        "get_question_collection_summary",
    ]
    # Check tool names registered on MCPServer
    tool_names = [t.name for t in asyncio_run(app.list_tools())]
    for expected in expected_tools:
        assert expected in tool_names, f"Tool '{expected}' should be registered."


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)


@pytest.mark.asyncio
async def test_mcp_list_departments(mock_env):
    service = mock_env["service"]
    depts = await service.list_departments()
    assert len(depts) == 2
    assert any(d["short_name"] == "CSE" for d in depts)


@pytest.mark.asyncio
async def test_mcp_list_courses(mock_env):
    service = mock_env["service"]
    courses = await service.list_courses("CSE")
    assert len(courses) == 2
    assert any(c["name"] == "Operating Systems" for c in courses)


@pytest.mark.asyncio
async def test_mcp_get_pdf_file_and_resource(mock_env):
    repo = mock_env["repo"]
    storage = mock_env["storage"]
    service = mock_env["service"]
    app = mock_env["app"]

    # Create dummy PDF on disk
    pdf_bytes = b"%PDF-1.4\nDIU Previous Exam Content\n%%EOF"
    meta = PDFMetadata(
        file_id="pdf_1949_1",
        question_id=1949,
        submission_id=1,
        department_short="CSE",
        department_name="Computer Science and Engineering",
        course_name="Operating Systems",
        course_code="227",
        semester="Fall 26",
        exam_type="quiz",
        section="A",
        batch="60",
        source_url="https://ourdiu.com/questions/1949",
        pdf_url="https://files.ourdiu.com/watermarked/sample.pdf",
        download_status="downloaded",
        file_size=len(pdf_bytes),
        sha256="dummy_sha256",
    )
    dest_path = storage.get_destination_path(meta)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(pdf_bytes)
    meta.local_path = str(dest_path.resolve())
    repo.upsert_pdf_file(meta)

    # 1. Test reading resource directly
    blob_res = read_pdf_resource(service, "pdf_1949_1")
    assert blob_res.uri == "diu-question://pdf/pdf_1949_1"
    assert blob_res.mime_type == "application/pdf"
    import base64
    assert base64.b64decode(blob_res.blob) == pdf_bytes

    # 2. Test tool invocation for get_pdf_file
    tool_result = await app.call_tool("get_pdf_file", {"file_id": "pdf_1949_1"})
    # Tool returns content items: TextContent (metadata) and EmbeddedResource (binary blob)
    assert len(tool_result.content) == 2
    assert tool_result.content[0].type == "text"
    assert "Operating Systems" in tool_result.content[0].text
    assert tool_result.content[1].type == "resource"
    assert tool_result.content[1].resource.mime_type == "application/pdf"
    assert base64.b64decode(tool_result.content[1].resource.blob) == pdf_bytes


@pytest.mark.asyncio
async def test_mcp_collection_summary(mock_env):
    repo = mock_env["repo"]
    service = mock_env["service"]

    # Insert a dummy PDF file record first to satisfy foreign key
    repo.upsert_pdf_file(
        PDFMetadata(
            file_id="pdf_1949_1",
            question_id=1949,
            submission_id=1,
            department_short="CSE",
            department_name="Computer Science and Engineering",
            course_name="Operating Systems",
            course_code="227",
            semester="Fall 26",
            exam_type="quiz",
            pdf_url="https://files.ourdiu.com/test.pdf",
            download_status="downloaded",
            file_size=12345,
            sha256="abc123sha",
        )
    )

    # Record a test collection
    repo.record_collection(
        collection_id="bundle_abc123",
        department="CSE",
        course="Operating Systems",
        semesters=["Fall 24"],
        exam_types=["midterm"],
        total_exams=2,
        total_pdfs=1,
        file_ids=["pdf_1949_1"],
    )

    summary = service.get_collection_summary("bundle_abc123")
    assert summary is not None
    assert summary["collection_id"] == "bundle_abc123"
    assert summary["department"] == "CSE"
    assert summary["course"] == "Operating Systems"

    # Test reading collection manifest resource
    manifest = read_collection_resource(service, "bundle_abc123")
    assert manifest.uri == "diu-question://collection/bundle_abc123"
    assert "bundle_abc123" in manifest.text
