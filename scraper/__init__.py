"""Scraper package for DIU Question MCP Server."""

from scraper.client import OurDIUClient, decode_turbo_stream_array
from scraper.departments import discover_departments
from scraper.courses import discover_courses
from scraper.semesters import (
    discover_semesters,
    discover_semesters_for_course,
    normalize_semester_str,
    semester_matches,
)
from scraper.exams import (
    discover_exam_types,
    discover_exam_types_for_course,
    normalize_exam_type,
    exam_type_matches,
)
from scraper.pagination import crawl_exam_records
from scraper.pdf_extractor import extract_submissions_for_exam

__all__ = [
    "OurDIUClient",
    "decode_turbo_stream_array",
    "discover_departments",
    "discover_courses",
    "discover_semesters",
    "discover_semesters_for_course",
    "normalize_semester_str",
    "semester_matches",
    "discover_exam_types",
    "discover_exam_types_for_course",
    "normalize_exam_type",
    "exam_type_matches",
    "crawl_exam_records",
    "extract_submissions_for_exam",
]
