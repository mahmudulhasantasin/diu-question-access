"""Database module for DIU Question MCP Server."""

from database.models import (
    Department, Course, Semester, ExamType, ExamRecord, PDFMetadata, CollectionRecord, CollectionSummary
)
from database.repository import DatabaseRepository

__all__ = [
    "Department",
    "Course",
    "Semester",
    "ExamType",
    "ExamRecord",
    "PDFMetadata",
    "CollectionRecord",
    "CollectionSummary",
    "DatabaseRepository",
]
