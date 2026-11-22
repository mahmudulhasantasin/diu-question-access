import asyncio
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.collection_service import CollectionService
from mcp_server.tools import create_mcp_server

async def main():
    print("=== LIVE INTEGRATION TEST ===")
    service = CollectionService()
    app = create_mcp_server(service=service)

    # 1. Discover departments live
    print("\n--- 1. Testing list_departments() ---")
    depts = await service.list_departments()
    print(f"Discovered {len(depts)} departments.")
    cse = next((d for d in depts if d["short_name"] == "CSE"), None)
    print("Found CSE department:", cse)
    assert cse is not None

    # 2. Discover courses under CSE live
    print("\n--- 2. Testing list_courses('CSE') ---")
    courses = await service.list_courses("CSE")
    print(f"Discovered {len(courses)} courses under CSE.")
    os_course = next((c for c in courses if "operating" in c["name"].lower()), None)
    print("Found Operating Systems course:", os_course)
    assert os_course is not None

    # 3. Discover semesters for Operating Systems
    print("\n--- 3. Testing list_semesters('CSE', 'Operating Systems') ---")
    semesters = await service.list_semesters("CSE", "Operating Systems")
    print(f"Discovered {len(semesters)} semesters for Operating Systems.")
    print("Sample semesters:", [s["name"] for s in semesters[:5]])

    # 4. Discover exam types for Operating Systems
    print("\n--- 4. Testing list_exam_types('CSE', 'Operating Systems') ---")
    exam_types = await service.list_exam_types("CSE", "Operating Systems")
    print("Available exam types:", [e["name"] for e in exam_types])

    # 5. Search questions (without downloading)
    print("\n--- 5. Testing search_questions('CSE', 'Operating Systems', semesters='Fall 26', exam_types=['quiz']) ---")
    search_res = await service.search_questions(
        department="CSE",
        course="Operating Systems",
        semesters="Fall 26",
        exam_types=["quiz"],
    )
    print(f"Search found {search_res['total_exams_found']} exams with {search_res['total_pdf_candidates']} PDF candidates.")
    assert search_res["total_exams_found"] > 0
    assert search_res["total_pdf_candidates"] > 0

    # 6. Collect questions (download real PDFs!)
    print("\n--- 6. Testing collect_questions('CSE', 'Operating Systems', semesters='Fall 26', exam_types=['quiz']) ---")
    summary = await service.collect_questions(
        department="CSE",
        course="Operating Systems",
        semesters="Fall 26",
        exam_types=["quiz"],
    )
    print("Collection Summary:")
    print("  Bundle ID:", summary.collection_id)
    print("  Total Exams Found:", summary.total_exams_found)
    print("  Total PDFs Collected:", summary.total_pdfs_collected)
    print("  Total File Size:", summary.total_file_size_formatted)
    print("  Semester Distribution:", summary.semester_distribution)
    print("  Exam Type Distribution:", summary.exam_type_distribution)
    print("  File IDs:", summary.file_ids)
    assert summary.total_pdfs_collected > 0
    assert len(summary.file_ids) > 0

    # 7. Test get_pdf_file via MCP tool call
    test_file_id = summary.file_ids[0]
    print(f"\n--- 7. Testing get_pdf_file('{test_file_id}') via MCP ---")
    mcp_result = await app.call_tool("get_pdf_file", {"file_id": test_file_id})
    print(f"Tool returned {len(mcp_result.content)} content blocks.")
    print("Block 0 (Text Content Metadata):")
    print(mcp_result.content[0].text[:400])
    print("Block 1 (Embedded Resource):")
    res = mcp_result.content[1].resource
    print("  URI:", res.uri)
    print("  MIME type:", res.mime_type)
    print("  Blob length:", len(res.blob))
    assert res.mime_type == "application/pdf"
    assert len(res.blob) > 1000

    # 8. Verify binary PDF on disk directly
    pdf_meta = service.get_pdf_metadata(test_file_id)
    disk_path = Path(pdf_meta.local_path)
    print(f"\n--- 8. Verifying PDF on disk at {disk_path} ---")
    assert disk_path.is_file()
    disk_bytes = disk_path.read_bytes()
    assert disk_bytes.startswith(b"%PDF-")
    print(f"Disk file exists, size: {len(disk_bytes)} bytes, starts with: {disk_bytes[:8]}")

    print("\n=== ALL LIVE INTEGRATION TESTS PASSED PERFECTLY! ===")

if __name__ == "__main__":
    asyncio.run(main())
