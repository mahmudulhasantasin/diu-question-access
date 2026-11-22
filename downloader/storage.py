"""Storage management for organized local PDF archiving."""

import logging
import re
from pathlib import Path
from typing import Optional
from config import DATA_DIR
from database.models import PDFMetadata

logger = logging.getLogger("diu_mcp.downloader.storage")


def sanitize_filename_part(part: str) -> str:
    """Sanitize path component for Windows and Unix compatibility."""
    if not part:
        return "unknown"
    # Replace invalid filesystem characters: <>:"/\|?*
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', part)
    # Replace spaces with underscores
    cleaned = re.sub(r'\s+', '_', cleaned.strip())
    # Strip dots or trailing underscores
    cleaned = cleaned.strip("._")
    return cleaned or "unknown"


class PDFStorageManager:
    """Calculates storage paths and manages PDF files on disk."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or DATA_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_destination_path(self, meta: PDFMetadata) -> Path:
        """Construct structured path:
        data/{Department}/{Course}/{Semester}/{exam_type}/question_{qid}_sub_{sid}.pdf
        """
        dept_part = sanitize_filename_part(meta.department_short or meta.department_name)
        course_part = sanitize_filename_part(meta.course_name)
        semester_part = sanitize_filename_part(meta.semester)
        exam_type_part = sanitize_filename_part(meta.exam_type)

        section_part = f"_sec_{sanitize_filename_part(meta.section)}" if meta.section else ""
        filename = f"question_{meta.question_id}_sub_{meta.submission_id}{section_part}.pdf"

        target_dir = self.base_dir / dept_part / course_part / semester_part / exam_type_part
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename

    def is_file_cached(self, path: Path, expected_sha256: Optional[str] = None) -> bool:
        """Check if file exists and optionally matches expected SHA-256."""
        if not path.is_file():
            return False
        if expected_sha256:
            import hashlib
            with open(path, "rb") as f:
                current_sha = hashlib.sha256(f.read()).hexdigest()
            return current_sha == expected_sha256
        return path.stat().st_size > 100
