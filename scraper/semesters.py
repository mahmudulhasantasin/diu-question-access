"""Semester discovery and flexible filter matching for OurDIU."""

import logging
import re
from typing import List, Union
from config import BROWSE_URL
from database.models import Semester
from scraper.client import OurDIUClient

logger = logging.getLogger("diu_mcp.scraper.semesters")


def normalize_semester_str(val: str) -> str:
    """Normalize semester names for comparison.
    Examples:
      'Fall 2024' -> 'fall 24'
      'Spring 25' -> 'spring 25'
      'Summer 2023' -> 'summer 23'
      'fall-24' -> 'fall 24'
      'fall24' -> 'fall 24'
    """
    if not val:
        return ""
    s = val.strip().lower()
    s = s.replace("-", " ").replace("'", "").replace("_", " ")
    # Replace 4-digit years with 2-digit years (e.g., 2024 -> 24)
    s = re.sub(r"\b20(\d{2})\b", r"\1", s)
    # Ensure space between season and year if condensed (e.g., fall24 -> fall 24)
    s = re.sub(r"(spring|summer|fall)(\d{2})", r"\1 \2", s)
    # Collapse extra whitespace
    return " ".join(s.split())


def semester_matches(
    semester_name: str,
    filter_value: Union[str, List[str]],
) -> bool:
    """Check if an actual semester matches the requested filter.
    Supports:
      - 'all' or '*'
      - Single string: 'Fall 2024' or 'Fall 24'
      - List of strings: ['Fall 2024', 'Spring 2025']
    """
    if isinstance(filter_value, str):
        if filter_value.strip().lower() in ("all", "*", "any", "all semesters", "all available semesters", ""):
            return True
        target_norm = normalize_semester_str(semester_name)
        filter_norm = normalize_semester_str(filter_value)
        return target_norm == filter_norm or filter_norm in target_norm or target_norm in filter_norm

    if isinstance(filter_value, list):
        if not filter_value:
            return True
        for f in filter_value:
            if isinstance(f, str) and f.strip().lower() in ("all", "*", "any", "all semesters"):
                return True
            if semester_matches(semester_name, f):
                return True
        return False

    return True


async def discover_semesters(client: OurDIUClient) -> List[Semester]:
    """Discover all global semesters dynamically from OurDIU."""
    logger.info("Discovering semesters from OurDIU...")
    page_data = await client.fetch_page_data(BROWSE_URL)
    loader_data = page_data.get("loaderData", {})
    questions_data = loader_data.get("routes/questions", {})
    raw_semesters = questions_data.get("semesters", [])

    semesters: List[Semester] = []
    if raw_semesters and isinstance(raw_semesters, list):
        for s in raw_semesters:
            if isinstance(s, dict) and "id" in s and "name" in s:
                semesters.append(
                    Semester(
                        id=int(s["id"]),
                        name=str(s["name"]),
                    )
                )

    if semesters:
        logger.info(f"Discovered {len(semesters)} semesters via turbo-stream.")
        return semesters

    # Fallback default if stream not available
    return [
        Semester(id=1, name="Spring 24"),
        Semester(id=10, name="Fall 24"),
        Semester(id=13, name="Spring 25"),
    ]


async def discover_semesters_for_course(
    client: OurDIUClient,
    department_id: int,
    course_id: int,
) -> List[Semester]:
    """Discover which semesters specifically have question papers for a course."""
    logger.info(f"Discovering semesters for course {course_id} in department {department_id}...")
    params = {
        "departmentId": str(department_id),
        "courseId": str(course_id),
    }
    page_data = await client.fetch_page_data(BROWSE_URL, params=params)
    loader_data = page_data.get("loaderData", {})
    questions_data = loader_data.get("routes/questions", {})
    items = questions_data.get("list", {}).get("items", [])

    seen_semesters = {}
    for item in items:
        sem = item.get("semester")
        if sem and isinstance(sem, dict) and "id" in sem and "name" in sem:
            sid = int(sem["id"])
            if sid not in seen_semesters:
                seen_semesters[sid] = Semester(id=sid, name=str(sem["name"]))

    if seen_semesters:
        # Return ordered from highest id (newest) to lowest
        res = sorted(seen_semesters.values(), key=lambda x: x.id, reverse=True)
        logger.info(f"Discovered {len(res)} course-specific semesters.")
        return res

    # Fallback to global semesters if none found
    return await discover_semesters(client)
