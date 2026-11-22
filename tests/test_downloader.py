"""Unit tests for PDF downloader, storage, and validator."""

import pytest
from pathlib import Path
from database.models import PDFMetadata
from downloader.validator import validate_pdf_bytes, compute_sha256
from downloader.storage import PDFStorageManager, sanitize_filename_part
from downloader.pdf_downloader import PDFDownloader


def test_validate_valid_pdf():
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    is_valid, sha, reason = validate_pdf_bytes(valid_pdf)
    assert is_valid is True
    assert len(sha) == 64
    assert sha == compute_sha256(valid_pdf)
    assert "Valid" in reason


def test_validate_html_rejection():
    # Attempting to disguise an HTML error page as a PDF
    html_data = (
        b"<!DOCTYPE html><html><head><title>Error</title></head>"
        b"<body><h1>Error 404: File Not Found</h1>"
        b"<p>The requested examination question could not be located on the server.</p></body></html>"
    )
    is_valid, sha, reason = validate_pdf_bytes(html_data)
    assert is_valid is False
    assert "Invalid magic header" in reason


def test_validate_empty_data():
    is_valid, sha, reason = validate_pdf_bytes(b"")
    assert is_valid is False
    assert "Empty" in reason


def test_sanitize_filename():
    assert sanitize_filename_part("CSE:221 / Algorithms * 2024?") == "CSE_221___Algorithms___2024"
    assert sanitize_filename_part("Computer Science & Engineering") == "Computer_Science_&_Engineering"
    assert sanitize_filename_part("Fall 24") == "Fall_24"


def test_storage_destination_path(tmp_path):
    storage = PDFStorageManager(base_dir=tmp_path)
    meta = PDFMetadata(
        file_id="pdf_1949_2967",
        question_id=1949,
        submission_id=2967,
        department_short="CSE",
        department_name="Computer Science and Engineering",
        course_name="Operating Systems",
        course_code="227",
        semester="Fall 26",
        exam_type="quiz",
        section="m",
        batch="66",
        source_url="https://ourdiu.com/questions/1949",
        pdf_url="https://files.ourdiu.com/test.pdf",
    )
    dest = storage.get_destination_path(meta)
    assert "CSE" in str(dest)
    assert "Operating_Systems" in str(dest)
    assert "Fall_26" in str(dest)
    assert "quiz" in str(dest)
    assert "question_1949_sub_2967_sec_m.pdf" in dest.name


def test_duplicate_cache_detection(tmp_path):
    storage = PDFStorageManager(base_dir=tmp_path)
    test_file = tmp_path / "sample.pdf"
    content = b"%PDF-1.4\nsample data\n%%EOF"
    test_file.write_bytes(content)
    sha = compute_sha256(content)

    assert storage.is_file_cached(test_file, expected_sha256=sha) is True
    assert storage.is_file_cached(test_file, expected_sha256="wrong_checksum") is False
    assert storage.is_file_cached(tmp_path / "nonexistent.pdf") is False


@pytest.mark.asyncio
async def test_pdf_downloader_success(tmp_path, monkeypatch):
    storage = PDFStorageManager(base_dir=tmp_path)
    downloader = PDFDownloader(storage_manager=storage)

    valid_bytes = b"%PDF-1.4\n" + b"exam questions " * 10 + b"\n%%EOF"

    class MockResponse:
        status_code = 200
        content = valid_bytes

    class MockAsyncClient:
        async def get(self, url):
            return MockResponse()

    meta = PDFMetadata(
        file_id="pdf_100_1",
        question_id=100,
        submission_id=1,
        department_short="CSE",
        department_name="Computer Science",
        course_name="Data Structures",
        course_code="85",
        semester="Fall 24",
        exam_type="midterm",
        pdf_url="https://files.ourdiu.com/fake.pdf",
    )

    result = await downloader.download_pdf(meta, client=MockAsyncClient())
    assert result.download_status == "downloaded"
    assert result.sha256 == compute_sha256(valid_bytes)
    assert Path(result.local_path).is_file()
    assert Path(result.local_path).read_bytes() == valid_bytes

    # Second download should use cache
    result2 = await downloader.download_pdf(result, client=MockAsyncClient(), force_refresh=False)
    assert result2.download_status == "cached"
