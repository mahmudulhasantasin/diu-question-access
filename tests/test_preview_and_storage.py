"""Tests for on-demand image preview rendering and storage limit management."""

import io
import pytest
import pypdfium2
from unittest.mock import AsyncMock, MagicMock, patch
from database.models import PDFMetadata
from database.repository import DatabaseRepository
from downloader.storage import PDFStorageManager
from services.preview_service import PreviewService


def _create_dummy_pdf_bytes(num_pages: int = 2) -> bytes:
    doc = pypdfium2.PdfDocument.new()
    for _ in range(num_pages):
        doc.new_page(200, 200)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_preview_service_renders_page_from_memory(tmp_path):
    db_file = tmp_path / "test.db"
    repo = DatabaseRepository(db_path=db_file)

    pdf_bytes = _create_dummy_pdf_bytes(2)
    meta = PDFMetadata(
        file_id="pdf_test_1",
        question_id=1,
        submission_id=1,
        department_short="CSE",
        department_name="Computer Science",
        course_name="Data Structures",
        course_code="CSE101",
        semester="Fall 2026",
        exam_type="midterm",
        pdf_url="https://ourdiu.com/dummy.pdf",
    )
    repo.upsert_pdf_file(meta)

    # Mock remote fetch
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = pdf_bytes

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    svc = PreviewService(repo=repo, client=mock_client)
    png_bytes, current_page, total_pages = await svc.get_page_png_bytes(
        file_id="pdf_test_1", page_number=1, scale=1.0
    )

    assert total_pages == 2
    assert current_page == 1
    assert len(png_bytes) > 0
    # PNG signature check: \x89PNG\r\n\x1a\n
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.asyncio
async def test_preview_service_out_of_range_page(tmp_path):
    db_file = tmp_path / "test.db"
    repo = DatabaseRepository(db_path=db_file)

    pdf_bytes = _create_dummy_pdf_bytes(1)
    local_pdf = tmp_path / "sample.pdf"
    local_pdf.write_bytes(pdf_bytes)

    meta = PDFMetadata(
        file_id="pdf_test_2",
        question_id=2,
        submission_id=1,
        department_short="CSE",
        department_name="Computer Science",
        course_name="Algorithms",
        course_code="CSE102",
        semester="Spring 2026",
        exam_type="final",
        local_path=str(local_pdf),
    )
    repo.upsert_pdf_file(meta)

    svc = PreviewService(repo=repo)
    with pytest.raises(ValueError, match="out of range"):
        await svc.get_page_png_bytes(file_id="pdf_test_2", page_number=5)


def test_storage_limit_enforcement(tmp_path):
    storage = PDFStorageManager(base_dir=tmp_path)

    # Create dummy files
    f1 = tmp_path / "old.pdf"
    f1.write_bytes(b"A" * 1000)

    f2 = tmp_path / "newer.pdf"
    f2.write_bytes(b"B" * 1000)

    assert storage.get_total_storage_bytes() == 2000

    # Limit to 1500 bytes -> should evict down to 75% (1125 bytes)
    freed = storage.enforce_storage_limit(max_bytes=1500)
    assert freed >= 1000
    assert storage.get_total_storage_bytes() <= 1500
