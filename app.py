"""Hugging Face Spaces Entrypoint: Unified Gradio Web UI + FastAPI REST API + MCP SSE Server."""

import io
import os
import logging
from typing import Optional
import gradio as gr
from PIL import Image

from api import create_app
from services.collection_service import CollectionService
from services.preview_service import PreviewService

logger = logging.getLogger("diu_mcp.app")

# 1. Initialize core FastAPI application with REST endpoints & MCP SSE
api_app = create_app()
service = CollectionService()
preview_service = PreviewService(repo=service.repo)


# 2. Gradio Interactive Functions
try:
    import spaces
    gpu_decorator = spaces.GPU
except Exception:
    def gpu_decorator(fn):
        return fn


@gpu_decorator
async def search_questions_ui(department: str, course: str, semester: str, exam_type: str):
    """Search OurDIU for exam questions and return a formatted markdown table."""
    dept = department.strip() or "CSE"
    c_query = course.strip() or "Data Structures"
    sem = semester.strip() if semester.strip() else "all"
    e_type = exam_type.lower().strip() if exam_type and exam_type != "All" else "all"

    try:
        results = await service.search_questions(
            department=dept,
            course=c_query,
            semesters=sem,
            exam_types=e_type,
        )

        exams = results.get("exams", [])
        if not exams:
            return "### ⚠️ No question papers found matching your query.", None

        md_output = [
            f"### 🎯 Found {len(exams)} Exams ({results.get('total_pdf_candidates', 0)} PDF submissions)",
            f"**Department:** {results.get('department_short')} | **Course:** {results.get('course')}\n",
            "| Exam ID | Semester | Exam Type | Submissions | Actions |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        first_file_id = None
        for item in exams:
            ex = item.get("exam", {})
            subs = item.get("submissions", [])
            sub_count = len(subs)
            sub_links = []
            for s in subs:
                fid = s.get("file_id")
                purl = s.get("pdf_url")
                if fid and not first_file_id:
                    first_file_id = fid
                if purl:
                    sub_links.append(f"[`{fid}`]({purl})")

            links_str = ", ".join(sub_links) if sub_links else "None"
            md_output.append(
                f"| `{ex.get('id')}` | **{ex.get('semester_name')}** | `{ex.get('exam_type_name')}` | {sub_count} | {links_str} |"
            )

        return "\n".join(md_output), first_file_id
    except Exception as e:
        logger.error(f"Search UI error: {e}")
        return f"### ❌ Error during search: {e}", None


@gpu_decorator
async def preview_page_ui(file_id: str, page_number: int):
    """Render a high-resolution PNG preview of the specified question page in-memory."""
    fid = file_id.strip()
    if not fid:
        return None, "Please enter a valid File ID (e.g. from the search results above)."

    try:
        png_bytes, p_num, total_pages = await preview_service.get_page_png_bytes(
            file_id=fid,
            page_number=int(page_number),
            scale=1.5,
        )
        img = Image.open(io.BytesIO(png_bytes))
        status_msg = f"✅ Rendered Page {p_num} of {total_pages} (High-DPI In-Memory, 0 Permanent Disk Space)"
        return img, status_msg
    except Exception as e:
        logger.error(f"Preview UI error for {fid}: {e}")
        return None, f"❌ Failed to render preview: {e}"


# 3. Build Gradio UI Blocks
with gr.Blocks(title="DIU Question MCP & REST Server") as demo:
    gr.Markdown(
        """
        # 🎓 DIU Previous Question Bank — MCP & REST API Server
        Universal **Model Context Protocol (MCP)** and **FastAPI** server for discovering, viewing, and delivering original DIU exam papers to AI Agents (**ChatGPT**, **Claude Desktop**, **Cursor IDE**).
        """
    )

    with gr.Tabs():
        with gr.TabItem("🔍 Search & Vision Preview"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 1. Search Question Papers")
                    dept_input = gr.Textbox(label="Department", value="CSE", placeholder="e.g. CSE, EEE, BBA")
                    course_input = gr.Textbox(label="Course Name / Code", value="Data Structures", placeholder="e.g. Operating Systems, Algorithms")
                    semester_input = gr.Textbox(label="Semester (Optional)", value="all", placeholder="e.g. Fall 26, Spring 24, all")
                    exam_type_input = gr.Dropdown(
                        label="Exam Type",
                        choices=["All", "Midterm", "Final", "Quiz"],
                        value="All",
                    )
                    search_btn = gr.Button("🔎 Search OurDIU Questions", variant="primary")

                with gr.Column(scale=2):
                    search_results_md = gr.Markdown("Enter search criteria and click Search to see available question papers.")

            gr.Markdown("---")

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 2. Multi-Modal Vision Page Preview")
                    gr.Markdown("Inspect exam pages, diagrams, circuits, and handwritten questions directly:")
                    preview_file_id = gr.Textbox(label="File ID", placeholder="e.g. pdf_1996_2999")
                    page_num_input = gr.Number(label="Page Number", value=1, precision=0)
                    preview_btn = gr.Button("🖼️ Render Page (In-Memory)", variant="secondary")
                    preview_status = gr.Markdown("")

                with gr.Column(scale=2):
                    page_image_output = gr.Image(label="Rendered Exam Question Page", type="pil")

            # Connect UI Events
            search_btn.click(
                fn=search_questions_ui,
                inputs=[dept_input, course_input, semester_input, exam_type_input],
                outputs=[search_results_md, preview_file_id],
            )

            preview_btn.click(
                fn=preview_page_ui,
                inputs=[preview_file_id, page_num_input],
                outputs=[page_image_output, preview_status],
            )

        with gr.TabItem("🤖 API & AI Integration Links"):
            gr.Markdown(
                """
                ### 🚀 Connect to ChatGPT, Claude Desktop, and Developers

                | Service / Endpoint | Direct URL | Description |
                | :--- | :--- | :--- |
                | **Interactive Swagger Docs** | [`/docs`](/docs) | Interactive testing for all REST endpoints |
                | **ChatGPT OpenAPI Schema** | [`/openapi.json`](/openapi.json) | Import directly into ChatGPT Custom Actions |
                | **Remote MCP SSE Endpoint** | [`/mcp`](/mcp) | Server-Sent Events stream for remote MCP clients |
                | **Health Check** | [`/health`](/health) | Uptime and database health status |
                | **Direct Page Image URL** | `/api/files/{id}/pages/{page}` | High-resolution on-demand PNG image |
                | **Direct PDF Download** | `/api/files/{id}/download` | Stream original binary PDF |

                ---

                #### 💬 How to Add to ChatGPT Custom GPT Actions:
                1. Open [chatgpt.com](https://chatgpt.com) $\to$ **Explore GPTs** $\to$ **Create a GPT**.
                2. Go to **Configure** $\to$ **Actions** $\to$ **Create new action**.
                3. Click **Import from URL** and paste your Space's URL:  
                   `https://<your-username>-<your-space-name>.hf.space/openapi.json`
                4. ChatGPT can now discover, analyze, and read all DIU questions!
                """
            )

# 4. Attach FastAPI REST, OpenAPI & MCP routes directly onto demo.app
for r in api_app.routes:
    if hasattr(r, "path") and r.path not in [x.path for x in demo.app.routes if hasattr(x, "path")]:
        demo.app.routes.append(r)

from mcp_server.tools import create_mcp_server
mcp_server_instance = create_mcp_server(service=service)
demo.app.mount("/mcp", mcp_server_instance.sse_app())

# Expose app for ASGI servers and launch demo for Hugging Face Spaces
app = demo.app

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, ssr_mode=False)
    demo.block_thread()
