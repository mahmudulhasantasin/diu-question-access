"""Course discovery for OurDIU."""

import logging
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from config import BROWSE_URL, BASE_URL
from database.models import Course
from scraper.client import OurDIUClient

logger = logging.getLogger("diu_mcp.scraper.courses")


async def discover_courses(
    client: OurDIUClient,
    department_id: int,
) -> List[Course]:
    """Discover all courses under a given department dynamically."""
    logger.info(f"Discovering courses for department ID {department_id}...")

    # Strategy 1: Fetch browse page with departmentId parameter
    params = {"departmentId": str(department_id)}
    page_data = await client.fetch_page_data(BROWSE_URL, params=params)
    loader_data = page_data.get("loaderData", {})
    questions_data = loader_data.get("routes/questions", {})
    raw_courses = questions_data.get("courses", [])

    courses: List[Course] = []
    if raw_courses and isinstance(raw_courses, list):
        for c in raw_courses:
            if isinstance(c, dict) and "id" in c and "name" in c:
                c_dept_id = c.get("departmentId")
                # Filter to only courses matching the department_id
                if c_dept_id is None or int(c_dept_id) == department_id:
                    aliases = c.get("aliases", [])
                    if not isinstance(aliases, list):
                        aliases = []
                    courses.append(
                        Course(
                            id=int(c["id"]),
                            name=str(c["name"]),
                            department_id=department_id,
                            published_count=int(c.get("publishedCount", 0)),
                            aliases=[str(a) for a in aliases if a],
                        )
                    )

    if courses:
        logger.info(f"Discovered {len(courses)} courses for department {department_id} via turbo-stream.")
        return sorted(courses, key=lambda x: x.name)

    # Strategy 2: Fallback to department page /questions/departments/{department_id}
    logger.info(f"Attempting fallback HTML discovery for department {department_id}...")
    dept_url = f"{BASE_URL}/questions/departments/{department_id}"
    html = await client.fetch_html(dept_url)
    soup = BeautifulSoup(html, "html.parser")

    # Look for course links or table items
    course_map = {}
    for a in soup.find_all("a", href=re.compile(r"courseId=(\d+)")):
        m = re.search(r"courseId=(\d+)", a["href"])
        if m:
            cid = int(m.group(1))
            name = a.get_text(strip=True)
            if name and cid not in course_map:
                course_map[cid] = name

    for cid, name in course_map.items():
        courses.append(
            Course(
                id=cid,
                name=name,
                department_id=department_id,
                published_count=0,
                aliases=[],
            )
        )

    logger.info(f"Discovered {len(courses)} courses via HTML fallback.")
    return sorted(courses, key=lambda x: x.name)
