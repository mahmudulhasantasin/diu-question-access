"""Pagination and multi-page exam record crawler for OurDIU."""

import logging
import math
import re
from typing import List, Optional, Union
from bs4 import BeautifulSoup
from config import BROWSE_URL, QUESTION_DETAIL_URL
from database.models import ExamRecord
from scraper.client import OurDIUClient
from scraper.semesters import semester_matches
from scraper.exams import exam_type_matches

logger = logging.getLogger("diu_mcp.scraper.pagination")


def parse_exam_records_from_stream(
    items: List[dict],
    default_dept_id: int,
    default_course_id: int,
) -> List[ExamRecord]:
    """Parse list of exam dictionaries from React Router stream."""
    records = []
    for it in items:
        if not isinstance(it, dict) or "id" not in it:
            continue
        try:
            qid = int(it["id"])
            dept = it.get("department") or {}
            course = it.get("course") or {}
            semester = it.get("semester") or {}
            exam_type = it.get("examType") or {}
            sub_counts = it.get("submissionCounts") or {}

            rec = ExamRecord(
                id=qid,
                department_id=int(dept.get("id", default_dept_id)),
                department_name=str(dept.get("name", "Unknown Department")),
                department_short=str(dept.get("shortName", "DIU")),
                course_id=int(course.get("id", default_course_id)),
                course_name=str(course.get("name", "Unknown Course")),
                semester_id=int(semester.get("id", 0)),
                semester_name=str(semester.get("name", "Unknown Semester")),
                exam_type_id=int(exam_type.get("id", 0)),
                exam_type_name=str(exam_type.get("name", "Unknown")),
                source_url=f"{QUESTION_DETAIL_URL}/{qid}",
                published_submissions=int(sub_counts.get("published", 1)),
            )
            records.append(rec)
        except Exception as e:
            logger.warning(f"Error parsing exam item {it.get('id')}: {e}")
    return records


def parse_exam_records_from_html(
    html: str,
    default_dept_id: int,
    default_course_id: int,
) -> List[ExamRecord]:
    """Fallback parser for HTML rendered question cards."""
    soup = BeautifulSoup(html, "html.parser")
    records = []

    for card in soup.find_all(class_=re.compile("card", re.I)):
        link = card.find("a", href=re.compile(r"^/questions/\d+"))
        if not link:
            continue
        m = re.search(r"^/questions/(\d+)", link["href"])
        if not m:
            continue
        qid = int(m.group(1))
        title = link.get_text(strip=True)

        # Look for semester and exam type badges or spans
        text_content = card.get_text(" ", strip=True)
        exam_type_name = "Final"
        if "midterm" in text_content.lower() or "mid" in text_content.lower():
            exam_type_name = "Midterm"
        elif "quiz" in text_content.lower():
            exam_type_name = "Quiz"

        # Look for semester pattern like 'Fall 24' or 'Spring 25'
        sem_match = re.search(r"\b(Fall|Spring|Summer)\s*(\d{2,4})\b", text_content, re.I)
        sem_name = f"{sem_match.group(1).capitalize()} {sem_match.group(2)}" if sem_match else "Unknown"

        rec = ExamRecord(
            id=qid,
            department_id=default_dept_id,
            department_name="DIU Department",
            department_short="DIU",
            course_id=default_course_id,
            course_name=title or "Course Exam",
            semester_id=0,
            semester_name=sem_name,
            exam_type_id=0,
            exam_type_name=exam_type_name,
            source_url=f"{QUESTION_DETAIL_URL}/{qid}",
            published_submissions=1,
        )
        records.append(rec)

    return records


async def crawl_exam_records(
    client: OurDIUClient,
    department_id: int,
    course_id: int,
    semesters: Union[str, List[str]] = "all",
    exam_types: Union[str, List[str]] = "all",
) -> List[ExamRecord]:
    """Crawl all pagination pages for the specified department and course, applying filters."""
    logger.info(
        f"Starting multi-page crawl for department={department_id}, course={course_id}, "
        f"semesters={semesters}, exam_types={exam_types}..."
    )

    all_matching_records: List[ExamRecord] = []
    seen_ids = set()
    current_page = 1
    total_pages = 1

    while current_page <= total_pages:
        params = {
            "departmentId": str(department_id),
            "courseId": str(course_id),
            "page": str(current_page),
        }
        logger.info(f"Crawling page {current_page} of {total_pages} (params={params})...")

        page_data = await client.fetch_page_data(BROWSE_URL, params=params)
        loader_data = page_data.get("loaderData", {})
        questions_data = loader_data.get("routes/questions", {})
        list_info = questions_data.get("list", {})

        page_records: List[ExamRecord] = []

        if list_info and "items" in list_info:
            total_items = int(list_info.get("total", 0))
            page_size = int(list_info.get("pageSize", 24))
            total_pages = max(1, math.ceil(total_items / page_size)) if page_size > 0 else 1
            raw_items = list_info.get("items", [])
            page_records = parse_exam_records_from_stream(raw_items, department_id, course_id)
        else:
            # Fallback to HTML
            page_records = parse_exam_records_from_html(
                page_data.get("html", ""), department_id, course_id
            )
            # Check pagination links in HTML
            soup = BeautifulSoup(page_data.get("html", ""), "html.parser")
            page_links = soup.find_all("a", href=re.compile(r"page=(\d+)"))
            max_p = current_page
            for pl in page_links:
                pm = re.search(r"page=(\d+)", pl["href"])
                if pm:
                    max_p = max(max_p, int(pm.group(1)))
            total_pages = max_p

        logger.info(
            f"Page {current_page}: found {len(page_records)} exam records (total pages: {total_pages})"
        )

        for rec in page_records:
            if rec.id in seen_ids:
                continue
            seen_ids.add(rec.id)

            # Apply semester filter
            if not semester_matches(rec.semester_name, semesters):
                logger.debug(
                    f"Skipping exam {rec.id}: semester '{rec.semester_name}' does not match '{semesters}'"
                )
                continue

            # Apply exam type filter
            if not exam_type_matches(rec.exam_type_name, exam_types):
                logger.debug(
                    f"Skipping exam {rec.id}: exam type '{rec.exam_type_name}' does not match '{exam_types}'"
                )
                continue

            all_matching_records.append(rec)

        current_page += 1

    logger.info(
        f"Completed crawl: found {len(all_matching_records)} exams matching filters "
        f"(out of {len(seen_ids)} total examined across {total_pages} pages)."
    )
    return all_matching_records
