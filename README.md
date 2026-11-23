# DIU Question Access — Production MCP & REST Server

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![MCP Specification](https://img.shields.io/badge/MCP-Protocol%20v2.3-purple.svg)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Render-Deployed%20Live-brightgreen.svg?logo=render)](https://diu-question-access.onrender.com)
[![Tests](https://img.shields.io/badge/Tests-36%20Passed-success.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A high-performance **Model Context Protocol (MCP)** and **FastAPI REST API** server that dynamically discovers, indexes, streams, and delivers Daffodil International University (DIU) examination question papers from the OurDIU repository.

Engineered for seamless integration with **ChatGPT (Custom MCP Plugins & Custom GPT Actions), Claude Desktop, Cursor IDE, Windsurf, and Web Browsers**.

---

## 🌐 Live Service Endpoints

The server is deployed live on cloud infrastructure:

| Endpoint | URL | Description |
| :--- | :--- | :--- |
| **Primary Root** | [https://diu-question-access.onrender.com/](https://diu-question-access.onrender.com/) | Live status & index summary |
| **MCP SSE Service** | `https://diu-question-access.onrender.com/mcp` | Server-Sent Events endpoint for MCP clients |
| **Interactive Docs** | [https://diu-question-access.onrender.com/docs](https://diu-question-access.onrender.com/docs) | Interactive Swagger UI (test in browser) |
| **OpenAPI Specification** | [https://diu-question-access.onrender.com/openapi.json](https://diu-question-access.onrender.com/openapi.json) | OpenAPI 3.1 schema for ChatGPT Actions |
| **Health Check** | [https://diu-question-access.onrender.com/health](https://diu-question-access.onrender.com/health) | Uptime and database health probe |

---

## 📖 How to Use (Integration Guide)

### 1. Connect to ChatGPT as a Custom MCP Plugin

Use ChatGPT's native **Custom MCP Server** integration to connect directly to the server:

1. Open **[ChatGPT](https://chatgpt.com)** in your browser.
2. Go to **Plugins** / **Developer Settings** $\to$ Click **Add custom MCP server**.
3. Fill in the connection form:
   * **Name**: `DIU Question Access`
   * **Description**: `Search past DIU examination question papers with high-resolution page previews.`
   * **Connection**: Select **Server URL**
   * **Server URL**: `https://diu-question-access.onrender.com/mcp`
   * **Authentication**: Select **No authentication** (None)
4. Check the box: ☑️ *"I understand and want to continue"*.
5. Click **Create as a plugin**.
6. The plugin will be created and activated. You can now chat directly with ChatGPT to query and preview question papers!

---

### 2. Connect to ChatGPT as a Custom GPT (Actions)

If you prefer building a dedicated **Custom GPT** with the OpenAPI schema:

1. In ChatGPT, go to **Explore GPTs** $\to$ Click **+ Create** (top right) $\to$ Select the **Configure** tab.
2. Configure basic info:
   * **Name**: `DIU Exam Assistant`
   * **Description**: `Search, summarize, and preview past Daffodil International University question papers.`
3. Scroll down to **Actions** $\to$ Click **Create new action**.
4. In the **Import from URL** input, paste:
   ```text
   https://diu-question-access.onrender.com/openapi.json
   ```
5. Click **Import**. ChatGPT will auto-populate all endpoints (`search_questions`, `collect_questions`, `list_departments`, `preview_question_page`, etc.).
6. Set **Authentication**: `None`.
7. Set **Privacy Policy**: `https://ourdiu.com`
8. In the **Instructions** box, paste:
   > "You are an academic assistant for Daffodil International University (DIU) students. Use the DIU Question actions to search past question papers by department, course, and semester. Transcribe questions clearly, provide high-resolution page previews when diagrams or formulas are discussed, and share direct download links."
9. Click **Save** (or **Publish**).

---

### 3. Connect to Claude Desktop

Connect Claude Desktop to the online cloud server or run locally via `stdio`:

#### Option A: Remote Cloud Connection (SSE)
Add to your Claude configuration (`%APPDATA%\Claude\claude_desktop_config.json` on Windows or `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "diu-question": {
      "url": "https://diu-question-access.onrender.com/mcp"
    }
  }
}
```

#### Option B: Local stdio Mode
```json
{
  "mcpServers": {
    "diu-question": {
      "command": "python",
      "args": [
        "c:\\Users\\tasin\\Downloads\\diu-question\\server.py",
        "--transport",
        "stdio"
      ],
      "cwd": "c:\\Users\\tasin\\Downloads\\diu-question"
    }
  }
}
```

---

### 4. Direct Browser Usage (Interactive Swagger UI)

You can explore and test all APIs directly without any AI client:

1. Visit: [https://diu-question-access.onrender.com/docs](https://diu-question-access.onrender.com/docs)
2. Click on any endpoint (e.g., `GET /api/departments` or `GET /api/courses`).
3. Click **Try it out** $\to$ Enter parameters $\to$ Click **Execute**.
4. Instant JSON responses or rendered page images will be displayed directly in your browser.

---

## 💬 Example Prompts to Try

Once connected to ChatGPT or Claude, try asking questions like:

### 1. Department & Course Exploration
* *"What departments are available in the DIU Question Bank?"*
* *"Show me all courses listed under the Computer Science and Engineering (CSE) department."*

### 2. Finding Question Papers
* *"Find previous Midterm exam questions for Operating Systems from Fall 2023 and Spring 2024."*
* *"Are there any Final exam papers for 'Algorithms' in the Software Engineering department?"*

### 3. Multimodal Page Preview (Vision Analysis)
* *"Can you preview page 1 of the Database Systems Midterm question to check the ER diagram?"*
* *"Show me the schematic or circuit diagram from question 3 of the Digital Logic Design exam paper."*
*(The server renders the exact PDF page as a high-resolution PNG image on-the-fly, allowing vision AI to analyze circuits, flowcharts, math equations, and handwritten notes).*

### 4. Topic Analysis & Exam Preparation
* *"Analyze the question patterns across the last 3 semesters for Artificial Intelligence. What topics appear most frequently?"*
* *"Create a practice quiz based on the Midterm questions collected for Compiler Design."*

### 5. Downloading Original PDFs
* *"Give me the direct PDF download link for the Spring 2024 Object Oriented Programming final exam."*

---

## 🛠️ MCP Tools Reference (10 Tools)

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `list_departments` | `force_refresh: bool` | Returns all academic departments discovered from OurDIU. |
| `list_courses` | `department: str, force_refresh: bool` | Returns courses under a specific department. |
| `list_semesters` | `department: str, course: str` | Lists available semesters with existing papers for the course. |
| `list_exam_types` | `department: str, course: str` | Lists exam categories (Midterm, Final, Quiz) for the course. |
| `search_questions` | `department, course, semesters, exam_types` | Queries available exams without downloading (preview mode). |
| `collect_questions` | `department, course, semesters, exam_types` | Collects papers, verifies binary headers, and registers records. |
| `list_collected_files` | `bundle_id: Optional[str]` | Lists downloaded/indexed questions with file identifiers. |
| `get_pdf_file` | `file_id: str` | Returns question text transcription, direct link, and file path. |
| `preview_question_page` | `file_id: str, page_number: int` | **Renders a page as high-res PNG image in-memory for AI vision.** |
| `get_question_collection_summary` | `collection_id: str` | Returns statistics regarding files, sizes, and categories. |

---

## 📡 REST API Reference

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Service root status & documentation index. |
| `HEAD` | `/` | Cloud orchestrator health check probe. |
| `GET` | `/health` | Service health status. |
| `GET` | `/docs` | Interactive Swagger documentation. |
| `GET` | `/openapi.json` | OpenAPI 3.1 specification for ChatGPT Actions. |
| `GET` | `/mcp` | MCP Server-Sent Events (SSE) streaming endpoint. |
| `GET` | `/api/departments` | Discovered department list. |
| `GET` | `/api/courses` | Department courses by query parameter. |
| `GET` | `/api/semesters` | Available semesters for a given course. |
| `GET` | `/api/exam-types` | Available exam categories for a given course. |
| `POST` | `/api/search` | Search papers without local disk storage. |
| `POST` | `/api/collect` | Collect papers and record database entries. |
| `GET` | `/api/files` | List collected/indexed question files. |
| `GET` | `/api/files/{file_id}` | Retrieve metadata and question text. |
| `GET` | `/api/files/{file_id}/download` | Stream binary PDF directly to browser/client. |
| `GET` | `/api/files/{file_id}/pages/{page}` | **Stream page as PNG image for browser/vision AI.** |
| `GET` | `/api/collections/{id}` | Session collection summary. |

---

## 💻 Local Development & Testing

### 1. Installation
```bash
git clone https://github.com/mahmudulhasantasin/diu-question-access.git
cd diu-question-access
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
```

### 2. Automated Tests (36 Tests)
```bash
python -m pytest -v
```

### 3. Run Locally
```bash
# REST API & MCP SSE
python server.py --transport http --host 0.0.0.0 --port 8000

# stdio mode (Claude Desktop)
python server.py --transport stdio
```

---

## 📜 License

This project is open-source and licensed under the [MIT License](LICENSE).
