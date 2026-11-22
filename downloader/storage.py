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

    def get_total_storage_bytes(self) -> int:
        """Calculate total size in bytes of all cached PDF files."""
        total = 0
        for p in self.base_dir.rglob("*.pdf"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
        return total

    def enforce_storage_limit(self, max_bytes: int = 50 * 1024 * 1024) -> int:
        """Evict oldest cached PDF files when storage exceeds max_bytes.

        Maintains an LRU policy based on file modification/access times,
        guaranteeing the server never runs out of disk quota on free hosting tiers.
        """
        current_bytes = self.get_total_storage_bytes()
        if current_bytes <= max_bytes:
            return 0

        target_bytes = int(max_bytes * 0.75)
        freed = 0

        files = []
        for p in self.base_dir.rglob("*.pdf"):
            if p.is_file():
                try:
                    stat = p.stat()
                    files.append((stat.st_mtime, p, stat.st_size))
                except OSError:
                    pass

        # Sort ascending by modification time (oldest first)
        files.sort(key=lambda item: item[0])

        for _, file_path, size in files:
            if current_bytes - freed <= target_bytes:
                break
            try:
                file_path.unlink(missing_ok=True)
                freed += size
                logger.info(f"Storage limit: evicted old cached file {file_path.name} ({size} bytes)")
            except OSError as exc:
                logger.warning(f"Could not remove {file_path}: {exc}")

        # Clean up empty parent directories
        for directory in sorted(self.base_dir.glob("**/*"), key=lambda p: len(str(p)), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                try:
                    directory.rmdir()
                except OSError:
                    pass

        return freed
