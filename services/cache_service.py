"""Caching service for departments, courses, and downloaded PDFs."""

import logging
from pathlib import Path
from typing import Optional, List
from database.models import Department, Course, Semester, ExamType, PDFMetadata  # noqa: F401 (public API)
from database.repository import DatabaseRepository

logger = logging.getLogger("diu_mcp.services.cache")


class CacheService:
    """Coordinates database caching and file existence verification."""

    def __init__(self, repo: DatabaseRepository):
        self.repo = repo

    def get_cached_departments(self) -> List[Department]:
        return self.repo.get_all_departments()

    def get_cached_courses(self, department_id: int) -> List[Course]:
        return self.repo.get_courses_by_department(department_id)

    def get_cached_semesters(self) -> List[Semester]:
        return self.repo.get_all_semesters()

    def get_cached_exam_types(self) -> List[ExamType]:
        return self.repo.get_all_exam_types()

    def find_cached_pdf(self, pdf_url: str) -> Optional[PDFMetadata]:
        meta = self.repo.get_pdf_by_url(pdf_url)
        if meta and meta.local_path and Path(meta.local_path).is_file():
            return meta
        return None

    def find_cached_by_sha256(self, sha256: str) -> Optional[PDFMetadata]:
        meta = self.repo.get_pdf_by_sha256(sha256)
        if meta and meta.local_path and Path(meta.local_path).is_file():
            return meta
        return None
