"""Collection service orchestrating discovery, search, download, and caching."""

import asyncio
import logging
import uuid
from typing import Optional, List, Dict, Any, Union
from database.models import (
    Department, Course, Semester, ExamType, ExamRecord, PDFMetadata, CollectionSummary
)
from database.repository import DatabaseRepository
from downloader.pdf_downloader import PDFDownloader
from scraper.client import OurDIUClient
from scraper.departments import discover_departments
from scraper.courses import discover_courses
from scraper.semesters import (
    discover_semesters,
    discover_semesters_for_course,
)
from scraper.exams import (
    discover_exam_types,
    discover_exam_types_for_course,
)
from scraper.pagination import crawl_exam_records
from scraper.pdf_extractor import extract_submissions_for_exam
from services.cache_service import CacheService
from services.metadata_service import MetadataService

logger = logging.getLogger("diu_mcp.services.collection")


class CollectionService:
    """Coordinates scraping, caching, downloading, and metadata retrieval."""

    def __init__(
        self,
        repo: Optional[DatabaseRepository] = None,
        client: Optional[OurDIUClient] = None,
        downloader: Optional[PDFDownloader] = None,
    ):
        self.repo = repo or DatabaseRepository()
        self.client = client or OurDIUClient()
        self.downloader = downloader or PDFDownloader()
        self.cache = CacheService(self.repo)

    async def list_departments(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """List all available departments dynamically from OurDIU with DB caching."""
        if not force_refresh:
            cached = self.cache.get_cached_departments()
            if cached:
                logger.info(f"Returning {len(cached)} cached departments.")
                return [d.to_dict() for d in cached]

        depts = await discover_departments(self.client)
        if depts:
            self.repo.upsert_departments(depts)
        return [d.to_dict() for d in depts]

    async def _resolve_department(self, dept_query: str) -> Department:
        """Resolve a department string (e.g. 'CSE', '5', 'Computer Science') to a Department object."""
        dept = self.repo.find_department(dept_query)
        if not dept:
            # Refresh departments from site
            depts = await discover_departments(self.client)
            self.repo.upsert_departments(depts)
            dept = self.repo.find_department(dept_query)

        if not dept:
            raise ValueError(
                f"Department '{dept_query}' not found. Please invoke list_departments() "
                "to see available departments."
            )
        return dept

    async def list_courses(self, department: str, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """List all courses under the specified department."""
        dept = await self._resolve_department(department)
        if not force_refresh:
            cached = self.cache.get_cached_courses(dept.id)
            if cached:
                logger.info(f"Returning {len(cached)} cached courses for department {dept.short_name}.")
                return [c.to_dict() for c in cached]

        courses = await discover_courses(self.client, dept.id)
        if courses:
            self.repo.upsert_courses(courses)
        return [c.to_dict() for c in courses]

    async def _resolve_course(self, department_id: int, course_query: str) -> Course:
        """Resolve a course name, code, or alias under a department."""
        course = self.repo.find_course(department_id, course_query)
        if not course:
            courses = await discover_courses(self.client, department_id)
            self.repo.upsert_courses(courses)
            course = self.repo.find_course(department_id, course_query)

        if not course:
            raise ValueError(
                f"Course '{course_query}' not found in department {department_id}. "
                "Please invoke list_courses(department) to see available courses."
            )
        return course

    async def list_semesters(self, department: str, course: str) -> List[Dict[str, Any]]:
        """List available semesters for the specified department and course."""
        dept = await self._resolve_department(department)
        c = await self._resolve_course(dept.id, course)
        semesters = await discover_semesters_for_course(self.client, dept.id, c.id)
        return [s.to_dict() for s in semesters]

    async def list_exam_types(self, department: str, course: str) -> List[Dict[str, Any]]:
        """List available exam types for the specified department and course."""
        dept = await self._resolve_department(department)
        c = await self._resolve_course(dept.id, course)
        exam_types = await discover_exam_types_for_course(self.client, dept.id, c.id)
        return [e.to_dict() for e in exam_types]

    async def search_questions(
        self,
        department: str,
        course: str,
        semesters: Union[str, List[str]] = "all",
        exam_types: Union[str, List[str]] = "all",
    ) -> Dict[str, Any]:
        """Search and find matching exam entries and their PDF download URLs without downloading."""
        dept = await self._resolve_department(department)
        c = await self._resolve_course(dept.id, course)

        matching_exams = await crawl_exam_records(
            self.client,
            department_id=dept.id,
            course_id=c.id,
            semesters=semesters,
            exam_types=exam_types,
        )

        # For each exam, extract the PDF submissions
        results = []
        total_pdf_candidates = 0

        # Run extraction with controlled concurrency
        sem = asyncio.Semaphore(5)

        async def get_subs(ex: ExamRecord):
            nonlocal total_pdf_candidates
            async with sem:
                subs = await extract_submissions_for_exam(self.client, ex)
                total_pdf_candidates += len(subs)
                return {
                    "exam": ex.to_dict(),
                    "pdf_count": len(subs),
                    "submissions": [s.to_dict() for s in subs],
                }

        tasks = [get_subs(ex) for ex in matching_exams]
        if tasks:
            results = await asyncio.gather(*tasks)

        return {
            "department": dept.name,
            "department_short": dept.short_name,
            "course": c.name,
            "course_id": c.id,
            "semesters_filter": semesters,
            "exam_types_filter": exam_types,
            "total_exams_found": len(matching_exams),
            "total_pdf_candidates": total_pdf_candidates,
            "exams": results,
        }

    async def collect_questions(
        self,
        department: str,
        course: str,
        semesters: Union[str, List[str]] = "all",
        exam_types: Union[str, List[str]] = "all",
        force_refresh: bool = False,
    ) -> CollectionSummary:
        """Collect and download all matching original PDFs, returning a structured summary."""
        dept = await self._resolve_department(department)
        c = await self._resolve_course(dept.id, course)

        logger.info(
            f"Collecting questions for {dept.short_name} - {c.name} "
            f"(semesters={semesters}, exam_types={exam_types}, force_refresh={force_refresh})..."
        )

        matching_exams = await crawl_exam_records(
            self.client,
            department_id=dept.id,
            course_id=c.id,
            semesters=semesters,
            exam_types=exam_types,
        )

        if not matching_exams:
            collection_id = f"bundle_{uuid.uuid4().hex[:8]}"
            sem_req = [semesters] if isinstance(semesters, str) else semesters
            et_req = [exam_types] if isinstance(exam_types, str) else exam_types
            summary = MetadataService.build_summary(
                collection_id=collection_id,
                department=dept.short_name,
                course=c.name,
                semesters_requested=sem_req,
                exam_types_requested=et_req,
                total_exams_found=0,
                files=[],
            )
            return summary

        # Extract all PDF metadata candidates
        sem_lock = asyncio.Semaphore(5)

        async def extract_one(ex: ExamRecord) -> List[PDFMetadata]:
            async with sem_lock:
                return await extract_submissions_for_exam(self.client, ex)

        extract_tasks = [extract_one(ex) for ex in matching_exams]
        nested_candidates = await asyncio.gather(*extract_tasks)
        all_candidates: List[PDFMetadata] = [sub for sub_list in nested_candidates for sub in sub_list]

        # Download PDFs with controlled concurrency
        download_semaphore = asyncio.Semaphore(4)
        client_instance = await self.client.get_client()

        async def download_one(meta: PDFMetadata) -> PDFMetadata:
            async with download_semaphore:
                res = await self.downloader.download_pdf(
                    meta, client=client_instance, force_refresh=force_refresh
                )
                self.repo.upsert_pdf_file(res)
                return res

        download_tasks = [download_one(meta) for meta in all_candidates]
        completed_files = await asyncio.gather(*download_tasks)

        # Record collection bundle in database
        collection_id = f"bundle_{uuid.uuid4().hex[:8]}"
        sem_req = [semesters] if isinstance(semesters, str) else semesters
        et_req = [exam_types] if isinstance(exam_types, str) else exam_types
        valid_ids = [f.file_id for f in completed_files if f.download_status in ("downloaded", "cached")]

        self.repo.record_collection(
            collection_id=collection_id,
            department=dept.short_name,
            course=c.name,
            semesters=sem_req,
            exam_types=et_req,
            total_exams=len(matching_exams),
            total_pdfs=len(valid_ids),
            file_ids=valid_ids,
        )

        summary = MetadataService.build_summary(
            collection_id=collection_id,
            department=dept.short_name,
            course=c.name,
            semesters_requested=sem_req,
            exam_types_requested=et_req,
            total_exams_found=len(matching_exams),
            files=completed_files,
        )
        return summary

    def list_collected_files(self, bundle_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List metadata for collected files, optionally filtered by bundle_id."""
        if bundle_id:
            files = self.repo.get_files_for_collection(bundle_id)
        else:
            with self.repo._get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM pdf_files WHERE download_status IN ('downloaded', 'cached') "
                    "ORDER BY download_timestamp DESC LIMIT 100"
                ).fetchall()
                files = []
                for r in rows:
                    d = dict(r)
                    d.pop("created_at", None)
                    files.append(PDFMetadata(**d))

        return [f.to_dict() for f in files]

    def get_pdf_metadata(self, file_id: str) -> Optional[PDFMetadata]:
        """Get metadata for a single file_id."""
        return self.repo.get_pdf_by_id(file_id)

    def get_collection_summary(self, collection_id: str) -> Optional[Dict[str, Any]]:
        """Get summary for an existing collection bundle."""
        bundle = self.repo.get_collection(collection_id)
        if not bundle:
            return None
        files = self.repo.get_files_for_collection(collection_id)
        summary = MetadataService.build_summary(
            collection_id=collection_id,
            department=bundle["department"],
            course=bundle["course"],
            semesters_requested=bundle["semesters"],
            exam_types_requested=bundle["exam_types"],
            total_exams_found=bundle["total_exams"],
            files=files,
        )
        return summary.model_dump()
