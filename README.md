# DIU Question Access — Production MCP & REST Server

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![MCP Specification](https://img.shields.io/badge/MCP-Protocol%20v2.3-purple.svg)](https://modelcontextprotocol.io/)
[![Framework](https://img.shields.io/badge/FastAPI-0.139-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Render-Deploy%20Ready-black.svg?logo=render)](https://render.com)
[![Tests](https://img.shields.io/badge/Tests-36%20Passed-success.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A high-performance **Model Context Protocol (MCP)** and **FastAPI REST API** server designed to dynamically discover, index, stream, and deliver examination question papers from the OurDIU repository.

Engineered for seamless integration with **ChatGPT (Custom GPT Actions), Claude Desktop, Cursor IDE, and Cloud Hosting (Render, Fly.io, Railway, Docker)**.

---

## Key Features

* **Binary Integrity**: Original PDF documents are downloaded and served directly without lossy conversions or vectorization.
* **On-Demand Page Preview (Multimodal Vision)**: Generates high-resolution PNG page images directly in-memory using `pypdfium2` so vision-enabled models (Claude 3.7 / 3.5 Sonnet, ChatGPT Vision) can inspect diagrams, circuit schematics, charts, and handwritten questions.
* **Zero-Storage Cloud Mode**: Streams PDFs and page images directly through memory buffers, avoiding disk exhaustion on free cloud hosting instances.
* **Storage Quota & Auto-Cleanup**: Enforces an automated LRU cache eviction policy to maintain local disk usage within user-defined quotas (default: $\le 50\text{ MB}$).
* **Universal Transports**:
  * **stdio**: Local IPC for Claude Desktop, Cursor, and VS Code.
  * **HTTP / REST**: OpenAPI 3.1 endpoints with Swagger UI for ChatGPT Custom Actions and web clients.
  * **SSE**: Server-Sent Events mounted at `/mcp` for remote MCP connections.
* **Dynamic Discovery**: Scrapes real-time department, course, semester, and exam category metadata without hardcoded assumptions.
* **IPC Crash Resilience**: Delivers clean question text transcriptions in tool responses to prevent client IPC buffer overruns on large documents.

---

## System Architecture

```
  +-------------------------------------------------------------+
  |                         AI Clients                          |
  |     Claude Desktop  |  ChatGPT GPT-4o  |  Cursor IDE        |
  +--------------+------------------------------+---------------+
                 |                              |
          JSON-RPC (stdio)              HTTP / REST / SSE
                 |                              |
  +--------------v------------------------------v---------------+
  |                 DIU Question Server Engine                  |
  |                    (server.py / api.py)                     |
  +-----------------------------+-------------------------------+
                                |
         +----------------------+----------------------+
         |                                             |
+--------v----------------------+             +--------v----------------------+
|       MCP Tools Engine        |             |        FastAPI REST API       |
| - list_departments            |             | - GET  / (Root & Health Index)|
| - list_courses                |             | - GET  /health                |
| - list_semesters              |             | - GET  /docs (Swagger UI)     |
| - list_exam_types             |             | - GET  /openapi.json          |
| - search_questions            |             | - GET  /mcp (SSE Endpoint)    |
| - collect_questions           |             | - POST /api/search            |
| - get_pdf_file                |             | - POST /api/collect           |
| - preview_question_page       |             | - GET  /api/files             |
| - list_collected_files        |             | - GET  /api/files/{id}/pages  |
| - get_collection_summary      |             | - GET  /api/files/{id}/down.. |
+-------------------------------+             +-------------------------------+
```

---

## Directory Layout

```
diu-question/
├── api.py                    # FastAPI REST API & OpenAPI 3.1 server
├── server.py                 # Multi-transport launcher (stdio, http, sse)
├── config.py                 # Central configuration and environment loader
├── Dockerfile                # Production multi-stage Docker build
├── docker-compose.yml        # Multi-container orchestration
├── pyproject.toml            # Project metadata and test configuration
├── requirements.txt          # Production dependencies
│
├── scraper/                  # Dynamic discovery & web extraction
│   ├── client.py             # Resilient async HTTP client with stream decoding
│   ├── departments.py        # Department extraction
│   ├── courses.py            # Course catalog discovery
│   ├── semesters.py          # Semester parsing and normalization
│   ├── exams.py              # Exam category filtering
│   ├── pagination.py         # Multi-page crawler traversal
│   └── pdf_extractor.py      # PDF URL and submission extraction
│
├── downloader/               # File downloading, validation & storage
│   ├── pdf_downloader.py     # Binary downloader with retry mechanics
│   ├── validator.py          # PDF header and checksum validation
│   └── storage.py            # Local path sanitization and LRU cleanup
│
├── services/                 # Domain logic and orchestration
│   ├── collection_service.py # Core search & collection coordinator
│   ├── preview_service.py    # On-the-fly page rendering for AI vision
│   ├── cache_service.py      # Cache validation logic
│   └── metadata_service.py   # Statistical reporting
│
├── database/                 # SQLite persistence layer
│   ├── models.py             # Data entities & schemas
│   └── repository.py         # SQLite database operations
│
└── tests/                    # Automated test suite (36 passing tests)
    ├── test_api.py           # REST endpoints, Root, and OpenAPI tests
    ├── test_downloader.py    # Download validation tests
    ├── test_filters.py       # Semester & exam normalization tests
    ├── test_hf_app.py        # Application integration tests
    ├── test_mcp.py           # MCP tool execution tests
    ├── test_preview_and_storage.py # Vision preview & LRU storage tests
    └── test_scraper.py       # Scraper and parser tests
```

---

## Setup & Local Installation

### 1. Clone the Repository
```bash
git clone https://github.com/mahmudulhasantasin/diu-question-access.git
cd diu-question-access
```

### 2. Environment Setup
```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration (Optional)
Create a `.env` file to configure custom host, port, or storage limits:
```env
DIU_SERVER_HOST=0.0.0.0
DIU_SERVER_PORT=8000
DIU_DATA_DIR=data
DIU_MAX_STORAGE_MB=50
```

---

## Running the Automated Tests

Execute the 36 automated tests covering all scrapers, downloaders, MCP tools, and REST endpoints:
```bash
python -m pytest -v
```

---

## Running the Server

### 1. Local MCP stdio Mode (Claude Desktop / Cursor)
Used for local desktop AI assistants:
```bash
python server.py --transport stdio
```

### 2. Production REST & MCP SSE Mode
Runs FastAPI with interactive Swagger UI and mounted MCP SSE:
```bash
python server.py --transport http --host 0.0.0.0 --port 8000
```
Interactive endpoints:
* **Root Index**: `http://localhost:8000/`
* **Swagger UI Docs**: `http://localhost:8000/docs`
* **OpenAPI 3.1 Schema**: `http://localhost:8000/openapi.json`
* **Health Check**: `http://localhost:8000/health`
* **MCP SSE Endpoint**: `http://localhost:8000/mcp`

### 3. Docker Container
```bash
docker compose up -d --build
```

---

## Free Cloud Deployment (Render)

Deploy this service online for **free** on Render:

1. Create a free account at [Render.com](https://render.com).
2. Click **New +** $\to$ **Web Service**.
3. Connect your GitHub repository: `diu-question-access`.
4. Render automatically detects the `Dockerfile` in the root:
   * **Runtime**: `Docker`
   * **Instance Type**: `Free`
5. Click **Deploy Web Service**.
6. Render builds the container, binds to port `8000`, and passes the health check.
7. You will receive a permanent HTTPS URL, for example: `https://diu-question-access.onrender.com`.

---

## Connecting with AI Clients

### 1. ChatGPT (Custom GPT Actions)
Connect the online Render service to ChatGPT:

1. Open ChatGPT and go to **Explore GPTs** $\to$ **Create a GPT** $\to$ **Configure**.
2. Scroll to the bottom and click **Create new action**.
3. In the **Import from URL** input, enter your Render OpenAPI schema URL:
   ```
   https://<your-render-service-name>.onrender.com/openapi.json
   ```
4. Click **Import**. ChatGPT will immediately configure all endpoints:
   * Searching questions by department, course, and semester.
   * Transcribing question text directly into the chat.
   * Previewing high-resolution PNG page images for diagrams, math equations, and circuit schematics.
   * Providing direct PDF download links.
5. In GPT Instructions, specify:
   > "You are an assistant for Daffodil International University students. Use the DIU Question actions to search past question papers, summarize them, and provide page preview images whenever users ask about diagrams or specific questions."

---

### 2. Claude Desktop Integration
Add the server entry to your Claude Desktop configuration file:

* **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
* **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

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

## MCP Tools Reference (10 Tools)

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `list_departments` | `force_refresh: bool` | Returns all academic departments discovered dynamically from OurDIU. |
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

## REST API Reference

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Service root status & documentation index. |
| `HEAD` | `/` | Cloud orchestrator health check probe. |
| `GET` | `/health` | Service health status. |
| `GET` | `/docs` | Interactive Swagger documentation. |
| `GET` | `/openapi.json` | OpenAPI 3.1 specification for ChatGPT Actions. |
| `GET` | `/mcp` | MCP Server-Sent Events (SSE) endpoint. |
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

## License

This project is open-source and licensed under the MIT License.
