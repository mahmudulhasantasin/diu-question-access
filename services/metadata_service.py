"""Metadata calculation and reporting service."""

from typing import List, Dict, Any
from database.models import PDFMetadata, CollectionSummary


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.2f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


class MetadataService:
    """Computes distributions and structured summaries from collected PDF files."""

    @staticmethod
    def build_summary(
        collection_id: str,
        department: str,
        course: str,
        semesters_requested: List[str],
        exam_types_requested: List[str],
        total_exams_found: int,
        files: List[PDFMetadata],
    ) -> CollectionSummary:
        semester_dist: Dict[str, int] = {}
        exam_type_dist: Dict[str, int] = {}
        download_failures: List[Dict[str, Any]] = []
        total_bytes = 0
        valid_file_ids: List[str] = []

        for f in files:
            if f.download_status in ("downloaded", "cached"):
                total_bytes += f.file_size
                valid_file_ids.append(f.file_id)

                sem = f.semester or "Unknown"
                semester_dist[sem] = semester_dist.get(sem, 0) + 1

                et = f.exam_type.capitalize() if f.exam_type else "Unknown"
                exam_type_dist[et] = exam_type_dist.get(et, 0) + 1
            else:
                download_failures.append({
                    "file_id": f.file_id,
                    "pdf_url": f.pdf_url,
                    "error": f.error_message or "Unknown download error",
                })

        return CollectionSummary(
            collection_id=collection_id,
            department=department,
            course=course,
            semesters_requested=semesters_requested,
            exam_types_requested=exam_types_requested,
            total_exams_found=total_exams_found,
            total_pdfs_collected=len(valid_file_ids),
            total_file_size_bytes=total_bytes,
            total_file_size_formatted=format_bytes(total_bytes),
            semester_distribution=semester_dist,
            exam_type_distribution=exam_type_dist,
            download_failures=download_failures,
            file_ids=valid_file_ids,
        )
