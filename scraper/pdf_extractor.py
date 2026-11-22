"""Original PDF URL and submission extraction from exam detail pages."""

import logging
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from config import QUESTION_DETAIL_URL
from database.models import ExamRecord, PDFMetadata
from scraper.client import OurDIUClient
from scraper.exams import normalize_exam_type

logger = logging.getLogger("diu_mcp.scraper.pdf_extractor")


async def extract_submissions_for_exam(
    client: OurDIUClient,
    exam: ExamRecord,
) -> List[PDFMetadata]:
    """Fetch exam detail page and extract all published PDF submissions."""
    url = f"{QUESTION_DETAIL_URL}/{exam.id}"
    logger.info(f"Extracting PDF submissions for exam {exam.id} ({exam.course_name} - {exam.semester_name})...")

    page_data = await client.fetch_page_data(url)
    loader_data = page_data.get("loaderData", {})
    route_q = loader_data.get("routes/question", {})
    q_data = route_q.get("question") or {}
    raw_submissions = q_data.get("submissions") or []

    pdf_entries: List[PDFMetadata] = []

    # Strategy 1: React Router loaderData
    if raw_submissions and isinstance(raw_submissions, list):
        for sub in raw_submissions:
            if not isinstance(sub, dict):
                continue
            status = sub.get("status", "published")
            if status != "published":
                continue

            file_url = sub.get("fileUrl")
            sub_id = sub.get("id", 1)
            file_size = int(sub.get("fileSize") or 0)
            section = sub.get("section")
            batch = sub.get("batch")
            sub_text = sub.get("text")

            if not file_url:
                continue

            # Ensure absolute URL
            if file_url.startswith("/"):
                file_url = f"{client.base_url}{file_url}"

            file_id = f"pdf_{exam.id}_{sub_id}"
            meta = PDFMetadata(
                file_id=file_id,
                question_id=exam.id,
                submission_id=sub_id,
                department_short=exam.department_short,
                department_name=exam.department_name,
                course_name=exam.course_name,
                course_code=str(exam.course_id),
                semester=exam.semester_name,
                exam_type=normalize_exam_type(exam.exam_type_name),
                section=str(section) if section else None,
                batch=str(batch) if batch else None,
                source_url=url,
                pdf_url=file_url,
                local_path="",
                download_status="pending",
                file_size=file_size,
                question_text=str(sub_text) if sub_text else None,
            )
            pdf_entries.append(meta)

    if pdf_entries:
        logger.info(f"Extracted {len(pdf_entries)} PDF submissions from stream for exam {exam.id}.")
        return pdf_entries

    # Strategy 2: Fallback to HTML parsing
    logger.info(f"Attempting HTML fallback extraction for exam {exam.id}...")
    html = page_data.get("html", "")
    soup = BeautifulSoup(html, "html.parser")

    seen_urls = set()
    sub_counter = 1

    # Look for object[data]
    for obj in soup.find_all("object", href=True):
        data_url = obj.get("data", "")
        if ".pdf" in data_url.lower():
            clean_url = data_url.split("#")[0]
            seen_urls.add(clean_url)

    # Look for links pointing to watermarked/ or .pdf
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower() or "watermarked" in href.lower():
            clean_url = href.split("#")[0]
            if clean_url.startswith("/"):
                clean_url = f"{client.base_url}{clean_url}"
            seen_urls.add(clean_url)

    for pdf_url in seen_urls:
        file_id = f"pdf_{exam.id}_{sub_counter}"
        meta = PDFMetadata(
            file_id=file_id,
            question_id=exam.id,
            submission_id=sub_counter,
            department_short=exam.department_short,
            department_name=exam.department_name,
            course_name=exam.course_name,
            course_code=str(exam.course_id),
            semester=exam.semester_name,
            exam_type=normalize_exam_type(exam.exam_type_name),
            section=None,
            batch=None,
            source_url=url,
            pdf_url=pdf_url,
            local_path="",
            download_status="pending",
            file_size=0,
        )
        pdf_entries.append(meta)
        sub_counter += 1

    logger.info(f"Extracted {len(pdf_entries)} PDF submissions via HTML fallback for exam {exam.id}.")
    return pdf_entries
