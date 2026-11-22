"""Exam type discovery, normalization, and filtering."""

import logging
import re
from typing import List, Union
from config import BROWSE_URL
from database.models import ExamType
from scraper.client import OurDIUClient

logger = logging.getLogger("diu_mcp.scraper.exams")


def normalize_exam_type(raw: str) -> str:
    """Normalize exam type labels according to DIU question specifications.
    
    Rules:
      - 'mid', 'midterm', 'midterm examination', 'mid-term' -> 'midterm'
      - 'final', 'final examination', 'term final' -> 'final'
      - 'quiz', 'class test', 'ct', 'class-test' -> 'quiz'
      - Preserves unknown/special exam types without corruption.
    """
    if not raw:
        return ""
    clean = raw.strip().lower()

    if clean in ("mid", "midterm", "mid-term", "mid term", "midterm examination", "mid examination", "mid_term"):
        return "midterm"
    if clean in ("final", "final examination", "term final", "semester final"):
        return "final"
    if clean in ("quiz", "class test", "class-test", "ct", "classtest"):
        return "quiz"
    
    # Substring matching for descriptive labels
    if "mid" in clean and "exam" in clean:
        return "midterm"
    if "final" in clean:
        return "final"
    if "quiz" in clean or "class test" in clean:
        return "quiz"

    # Preserve unknown exam types
    return clean


def exam_type_matches(
    actual_exam_type: str,
    filter_value: Union[str, List[str]],
) -> bool:
    """Check if actual exam type matches requested filter(s).
    
    Supports:
      - 'all' or '*'
      - 'midterm', 'final', 'quiz'
      - list: ['midterm', 'final']
    """
    actual_norm = normalize_exam_type(actual_exam_type)

    if isinstance(filter_value, str):
        if filter_value.strip().lower() in ("all", "*", "any", "all exam types", "all types", ""):
            return True
        return actual_norm == normalize_exam_type(filter_value)

    if isinstance(filter_value, list):
        if not filter_value:
            return True
        for f in filter_value:
            if isinstance(f, str) and f.strip().lower() in ("all", "*", "any", "all exam types"):
                return True
            if actual_norm == normalize_exam_type(f):
                return True
        return False

    return True


async def discover_exam_types(client: OurDIUClient) -> List[ExamType]:
    """Discover all exam types dynamically from OurDIU."""
    logger.info("Discovering exam types from OurDIU...")
    page_data = await client.fetch_page_data(BROWSE_URL)
    loader_data = page_data.get("loaderData", {})
    questions_data = loader_data.get("routes/questions", {})
    raw_types = questions_data.get("examTypes", [])

    exam_types: List[ExamType] = []
    if raw_types and isinstance(raw_types, list):
        for e in raw_types:
            if isinstance(e, dict) and "id" in e and "name" in e:
                name = str(e["name"])
                exam_types.append(
                    ExamType(
                        id=int(e["id"]),
                        name=name,
                        normalized=normalize_exam_type(name),
                    )
                )

    if exam_types:
        logger.info(f"Discovered {len(exam_types)} exam types via turbo-stream.")
        return exam_types

    # Fallback to standard DIU exam types
    return [
        ExamType(id=4, name="Midterm", normalized="midterm"),
        ExamType(id=1, name="Final", normalized="final"),
        ExamType(id=5, name="Quiz", normalized="quiz"),
    ]


async def discover_exam_types_for_course(
    client: OurDIUClient,
    department_id: int,
    course_id: int,
) -> List[ExamType]:
    """Discover exam types that are actually available for a specific course."""
    logger.info(f"Discovering exam types for course {course_id}...")
    params = {
        "departmentId": str(department_id),
        "courseId": str(course_id),
    }
    page_data = await client.fetch_page_data(BROWSE_URL, params=params)
    loader_data = page_data.get("loaderData", {})
    questions_data = loader_data.get("routes/questions", {})
    items = questions_data.get("list", {}).get("items", [])

    seen_types = {}
    for item in items:
        et = item.get("examType")
        if et and isinstance(et, dict) and "id" in et and "name" in et:
            eid = int(et["id"])
            if eid not in seen_types:
                name = str(et["name"])
                seen_types[eid] = ExamType(
                    id=eid,
                    name=name,
                    normalized=normalize_exam_type(name),
                )

    if seen_types:
        return list(seen_types.values())

    return await discover_exam_types(client)
