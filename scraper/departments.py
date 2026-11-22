"""Department discovery for OurDIU."""

import logging
import re
from typing import List
from bs4 import BeautifulSoup
from config import BROWSE_URL, DEPARTMENTS_URL
from database.models import Department
from scraper.client import OurDIUClient

logger = logging.getLogger("diu_mcp.scraper.departments")


async def discover_departments(client: OurDIUClient) -> List[Department]:
    """Discover all departments dynamically from OurDIU."""
    logger.info("Discovering departments from OurDIU...")

    # Strategy 1: Fetch browse page which contains full departments array in React Router stream
    page_data = await client.fetch_page_data(BROWSE_URL)
    loader_data = page_data.get("loaderData", {})
    questions_data = loader_data.get("routes/questions", {})
    raw_depts = questions_data.get("departments", [])

    departments: List[Department] = []
    if raw_depts and isinstance(raw_depts, list):
        for d in raw_depts:
            if isinstance(d, dict) and "id" in d and "name" in d:
                departments.append(
                    Department(
                        id=int(d["id"]),
                        name=str(d["name"]),
                        short_name=str(d.get("shortName", d["name"][:4].upper())),
                        published_count=int(d.get("publishedCount", 0)),
                    )
                )

    if departments:
        logger.info(f"Discovered {len(departments)} departments via turbo-stream.")
        return sorted(departments, key=lambda x: x.name)

    # Strategy 2: Fallback to HTML parsing of /questions/departments
    logger.info("Attempting fallback HTML discovery for departments...")
    html = await client.fetch_html(DEPARTMENTS_URL)
    soup = BeautifulSoup(html, "html.parser")
    dept_map = {}

    for a in soup.find_all("a", href=re.compile(r"/questions/departments/\d+")):
        href = a["href"]
        m = re.search(r"/questions/departments/(\d+)", href)
        if m:
            dept_id = int(m.group(1))
            name = a.get_text(strip=True)
            if name and dept_id not in dept_map:
                dept_map[dept_id] = name

    for dept_id, name in dept_map.items():
        short_name = name
        # If format is "Computer Science and Engineering (CSE)"
        m = re.search(r"\(([^)]+)\)", name)
        if m:
            short_name = m.group(1)
            name = name[:m.start()].strip()
        departments.append(
            Department(
                id=dept_id,
                name=name,
                short_name=short_name,
                published_count=0,
            )
        )

    logger.info(f"Discovered {len(departments)} departments via HTML fallback.")
    return sorted(departments, key=lambda x: x.name)
