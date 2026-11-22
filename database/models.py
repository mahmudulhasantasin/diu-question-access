"""Data models for DIU Question MCP Server."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


@dataclass
class Department:
    """Academic department model."""
    id: int
    name: str
    short_name: str
    published_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "published_count": self.published_count,
        }


@dataclass
class Course:
    """Course under a department."""
    id: int
    name: str
    department_id: int
    published_count: int = 0
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "department_id": self.department_id,
            "published_count": self.published_count,
            "aliases": self.aliases,
        }


@dataclass
class Semester:
    """Academic semester model."""
    id: int
    name: str  # e.g., "Fall 24" or "Spring 25"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
        }


@dataclass
class ExamType:
    """Exam category model (Midterm, Final, Quiz)."""
    id: int
    name: str
    normalized: str  # e.g., "midterm", "final", "quiz"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "normalized": self.normalized,
        }


@dataclass
class ExamRecord:
    """An examination entry grouping one or more submissions/PDFs."""
    id: int
    department_id: int
    department_name: str
    department_short: str
    course_id: int
    course_name: str
    semester_id: int
    semester_name: str
    exam_type_id: int
    exam_type_name: str
    source_url: str
    published_submissions: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "department_id": self.department_id,
            "department_name": self.department_name,
            "department_short": self.department_short,
            "course_id": self.course_id,
            "course_name": self.course_name,
            "semester_id": self.semester_id,
            "semester_name": self.semester_name,
            "exam_type_id": self.exam_type_id,
            "exam_type_name": self.exam_type_name,
            "source_url": self.source_url,
            "published_submissions": self.published_submissions,
        }


@dataclass
class PDFMetadata:
    """Complete metadata for a single collected PDF document."""
    file_id: str
    question_id: int
    submission_id: int
    department_short: str
    department_name: str
    course_name: str
    course_code: str
    semester: str
    exam_type: str
    section: Optional[str] = None
    batch: Optional[str] = None
    source_url: str = ""
    pdf_url: str = ""
    local_path: str = ""
    download_status: str = "pending"  # "downloaded", "failed", "cached"
    download_timestamp: Optional[str] = None
    file_size: int = 0
    sha256: Optional[str] = None
    error_message: Optional[str] = None
    question_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "question_id": self.question_id,
            "submission_id": self.submission_id,
            "department_short": self.department_short,
            "department_name": self.department_name,
            "course_name": self.course_name,
            "course_code": self.course_code,
            "semester": self.semester,
            "exam_type": self.exam_type,
            "section": self.section,
            "batch": self.batch,
            "source_url": self.source_url,
            "pdf_url": self.pdf_url,
            "local_path": self.local_path,
            "download_status": self.download_status,
            "download_timestamp": self.download_timestamp,
            "file_size": self.file_size,
            "sha256": self.sha256,
            "error_message": self.error_message,
            "question_text": self.question_text,
        }


@dataclass
class CollectionRecord:
    """A collection/bundle session."""
    collection_id: str
    department: str
    course: str
    semesters: List[str]
    exam_types: List[str]
    total_exams: int
    total_pdfs: int
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CollectionSummary(BaseModel):
    """Structured summary of a collection operation."""
    collection_id: str = Field(description="Unique identifier for this collection bundle")
    department: str = Field(description="Selected department name or code")
    course: str = Field(description="Selected course name or code")
    semesters_requested: List[str] = Field(description="Semesters filter requested")
    exam_types_requested: List[str] = Field(description="Exam types filter requested")
    total_exams_found: int = Field(description="Number of matching exam entries on OurDIU")
    total_pdfs_collected: int = Field(description="Number of valid PDF files collected")
    total_file_size_bytes: int = Field(description="Total size of all collected PDFs in bytes")
    total_file_size_formatted: str = Field(description="Human readable file size, e.g. 1.25 MB")
    semester_distribution: Dict[str, int] = Field(description="Count of PDFs per semester")
    exam_type_distribution: Dict[str, int] = Field(description="Count of PDFs per exam type")
    download_failures: List[Dict[str, Any]] = Field(default_factory=list, description="Details of any failed downloads")
    file_ids: List[str] = Field(default_factory=list, description="List of file_ids for retrieving PDFs")
