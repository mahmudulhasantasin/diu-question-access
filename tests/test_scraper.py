"""Unit tests for OurDIU scraper, turbo-stream decoding, and pagination."""

import pytest
from database.models import ExamRecord
from scraper.client import decode_turbo_stream_array, OurDIUClient
from scraper.departments import discover_departments
from scraper.courses import discover_courses
from scraper.pagination import crawl_exam_records, parse_exam_records_from_stream
from scraper.pdf_extractor import extract_submissions_for_exam


def test_decode_turbo_stream_array():
    # Construct a synthetic turbo-stream array:
    # index 0: root dict with key pointer to 1 ('loaderData'), value pointer to 2
    # index 1: 'loaderData'
    # index 2: dict with key pointer to 3 ('departments'), value pointer to 4
    # index 3: 'departments'
    # index 4: list of pointers [5]
    # index 5: dict for department {'_6': 7, '_8': 9}
    # index 6: 'id', index 7: 5, index 8: 'name', index 9: 'CSE'
    stream = [
        {"_1": 2},
        "loaderData",
        {"_3": 4},
        "departments",
        [5],
        {"_6": 7, "_8": 9},
        "id",
        5,
        "name",
        "CSE"
    ]
    decoded = decode_turbo_stream_array(stream)
    assert isinstance(decoded, dict)
    assert "loaderData" in decoded
    assert "departments" in decoded["loaderData"]
    depts = decoded["loaderData"]["departments"]
    assert len(depts) == 1
    assert depts[0]["id"] == 5
    assert depts[0]["name"] == "CSE"


@pytest.mark.asyncio
async def test_discover_departments_mocked(monkeypatch):
    client = OurDIUClient()

    async def mock_fetch_page_data(url, params=None):
        return {
            "loaderData": {
                "routes/questions": {
                    "departments": [
                        {"id": 5, "name": "Computer Science and Engineering", "shortName": "CSE", "publishedCount": 730},
                        {"id": 7, "name": "Electrical and Electronic Engineering", "shortName": "EEE", "publishedCount": 120},
                    ]
                }
            }
        }

    monkeypatch.setattr(client, "fetch_page_data", mock_fetch_page_data)
    depts = await discover_departments(client)
    assert len(depts) == 2
    assert depts[0].short_name == "CSE"
    assert depts[1].short_name == "EEE"


@pytest.mark.asyncio
async def test_discover_courses_mocked(monkeypatch):
    client = OurDIUClient()

    async def mock_fetch_page_data(url, params=None):
        return {
            "loaderData": {
                "routes/questions": {
                    "courses": [
                        {"id": 227, "name": "Operating Systems", "departmentId": 5, "publishedCount": 14, "aliases": ["os"]},
                        {"id": 85, "name": "Data Structures", "departmentId": 5, "publishedCount": 37, "aliases": ["ds", "dsa"]},
                        {"id": 99, "name": "Circuits I", "departmentId": 7, "publishedCount": 10, "aliases": []},
                    ]
                }
            }
        }

    monkeypatch.setattr(client, "fetch_page_data", mock_fetch_page_data)
    courses = await discover_courses(client, department_id=5)
    # Only CSE courses (departmentId 5) should be returned
    assert len(courses) == 2
    assert courses[0].name == "Data Structures"
    assert courses[1].name == "Operating Systems"
    assert "os" in courses[1].aliases


@pytest.mark.asyncio
async def test_pagination_and_filtering(monkeypatch):
    client = OurDIUClient()

    # Simulate multi-page response (page 1 has 2 items, total is 4, page_size is 2)
    async def mock_fetch_page_data(url, params=None):
        page = int(params.get("page", 1))
        if page == 1:
            return {
                "loaderData": {
                    "routes/questions": {
                        "list": {
                            "total": 4,
                            "page": 1,
                            "pageSize": 2,
                            "items": [
                                {
                                    "id": 101,
                                    "department": {"id": 5, "name": "CSE", "shortName": "CSE"},
                                    "course": {"id": 227, "name": "Operating Systems"},
                                    "semester": {"id": 20, "name": "Fall 24"},
                                    "examType": {"id": 4, "name": "Midterm"},
                                    "submissionCounts": {"published": 1},
                                },
                                {
                                    "id": 102,
                                    "department": {"id": 5, "name": "CSE", "shortName": "CSE"},
                                    "course": {"id": 227, "name": "Operating Systems"},
                                    "semester": {"id": 13, "name": "Spring 25"},
                                    "examType": {"id": 1, "name": "Final"},
                                    "submissionCounts": {"published": 2},
                                },
                            ]
                        }
                    }
                }
            }
        else:
            return {
                "loaderData": {
                    "routes/questions": {
                        "list": {
                            "total": 4,
                            "page": 2,
                            "pageSize": 2,
                            "items": [
                                {
                                    "id": 103,
                                    "department": {"id": 5, "name": "CSE", "shortName": "CSE"},
                                    "course": {"id": 227, "name": "Operating Systems"},
                                    "semester": {"id": 20, "name": "Fall 24"},
                                    "examType": {"id": 5, "name": "Quiz"},
                                    "submissionCounts": {"published": 1},
                                },
                                {
                                    "id": 104,
                                    "department": {"id": 5, "name": "CSE", "shortName": "CSE"},
                                    "course": {"id": 227, "name": "Operating Systems"},
                                    "semester": {"id": 13, "name": "Spring 25"},
                                    "examType": {"id": 4, "name": "Midterm"},
                                    "submissionCounts": {"published": 1},
                                },
                            ]
                        }
                    }
                }
            }

    monkeypatch.setattr(client, "fetch_page_data", mock_fetch_page_data)

    # 1. Crawl with all semesters and all exam types -> should collect all 4 across both pages
    all_exams = await crawl_exam_records(client, department_id=5, course_id=227, semesters="all", exam_types="all")
    assert len(all_exams) == 4

    # 2. Crawl with single semester 'Fall 2024' -> should match Fall 24 items (101 and 103)
    fall_exams = await crawl_exam_records(client, department_id=5, course_id=227, semesters="Fall 2024", exam_types="all")
    assert len(fall_exams) == 2
    assert {e.id for e in fall_exams} == {101, 103}

    # 3. Crawl with exam_types=['midterm'] -> should match Midterm items (101 and 104)
    mid_exams = await crawl_exam_records(client, department_id=5, course_id=227, semesters="all", exam_types=["midterm"])
    assert len(mid_exams) == 2
    assert {e.id for e in mid_exams} == {101, 104}


@pytest.mark.asyncio
async def test_extract_submissions_for_exam(monkeypatch):
    client = OurDIUClient()

    async def mock_fetch_page_data(url, params=None):
        return {
            "loaderData": {
                "routes/question": {
                    "question": {
                        "id": 1949,
                        "submissions": [
                            {
                                "id": 1,
                                "status": "published",
                                "section": "A",
                                "batch": "60",
                                "fileUrl": "https://files.ourdiu.com/sub1.pdf",
                                "fileSize": 150000,
                            },
                            {
                                "id": 2,
                                "status": "published",
                                "section": "B",
                                "batch": "60",
                                "fileUrl": "https://files.ourdiu.com/sub2.pdf",
                                "fileSize": 180000,
                            },
                            {
                                "id": 3,
                                "status": "pendingReview",  # Should be ignored
                                "fileUrl": "https://files.ourdiu.com/pending.pdf",
                            }
                        ]
                    }
                }
            }
        }

    monkeypatch.setattr(client, "fetch_page_data", mock_fetch_page_data)

    exam = ExamRecord(
        id=1949,
        department_id=5,
        department_name="CSE",
        department_short="CSE",
        course_id=227,
        course_name="Operating Systems",
        semester_id=20,
        semester_name="Fall 26",
        exam_type_id=5,
        exam_type_name="Quiz",
        source_url="https://ourdiu.com/questions/1949",
    )

    subs = await extract_submissions_for_exam(client, exam)
    assert len(subs) == 2
    assert subs[0].file_id == "pdf_1949_1"
    assert subs[0].pdf_url == "https://files.ourdiu.com/sub1.pdf"
    assert subs[1].file_id == "pdf_1949_2"
    assert subs[1].section == "B"
