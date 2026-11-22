# DIU Question Access — Production MCP & REST Server

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![MCP Specification](https://img.shields.io/badge/MCP-Protocol%20v2.3-purple.svg)](https://modelcontextprotocol.io/)
[![Framework](https://img.shields.io/badge/FastAPI-0.139-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-34%20Passed-success.svg)]()

A high-performance **Model Context Protocol (MCP)** and **FastAPI REST API** server designed to dynamically discover, index, stream, and deliver examination question papers from the OurDIU repository.

Engineered for seamless integration with **Claude Desktop, ChatGPT (Custom GPT Actions), Cursor IDE, and Cloud Hosting (Render, Fly.io, Railway, Docker)**.

---

## Highlights

* **Binary Integrity**: Original PDF documents are downloaded and served without lossy conversions or vectorization.
* **On-Demand Page Preview (Multimodal Vision)**: Generates high-resolution PNG page images directly in-memory so vision-enabled models (Claude, ChatGPT Vision) can inspect diagrams, circuit schematics, charts, and handwritten questions.
* **Zero-Storage Cloud Mode**: Streams PDFs and page images directly through memory buffers, avoiding disk exhaustion on free cloud hosting instances.
* **Storage Quota & Auto-Cleanup**: Enforces an automated LRU cache eviction policy to maintain local disk usage within user-defined quotas.
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
| - list_departments            |             | - GET  /health                |
| - list_courses                |             | - GET  /docs (Swagger UI)     |
| - list_semesters              |             | - GET  /openapi.json          |
| - list_exam_types             |             | - POST /api/search            |
| - search_questions            |             | - POST /api/collect           |
| - collect_questions           |             | - GET  /api/files/{id}/pages  |
| - get_pdf_file                |             | - GET  /api/files/{id}/down.. |
| - preview_question_page (NEW) |             +-------------------------------+
| - list_collected_files        |
| - get_collection_summary      |
+-------------------------------+
```

---

## Directory Layout

```
diu-question/
├── api.py                    # FastAPI REST API & OpenAPI 3.1 server
├── server.py                 # Multi-transport launcher (stdio, http, sse)
├── config.py                 # Central configuration and environment loader
├── Dockerfile                # Production container build definition
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
└── tests/                    # Automated test suite (34 passing tests)
    ├── test_api.py           # REST endpoints and OpenAPI tests
    ├── test_downloader.py    # Download validation tests
    ├── test_filters.py       # Semester & exam normalization tests
    ├── test_mcp.py           # MCP tool execution tests
    ├── test_preview_and_storage.py # Vision preview & LRU storage tests
    └── test_scraper.py       # Scraper and parser tests
```

---

## Setup & Installation

### 1. Clone & Navigate
```bash
git clone https://github.com/mahmudulhasantasin/diu-question-access.git
cd diu-question-access
```

### 2. Environment Setup
```bash
# Windows
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

### 4. Configuration
Create a `.env` file if custom ports or directories are required:
```env
DIU_SERVER_HOST=0.0.0.0
DIU_SERVER_PORT=8000
DIU_DATA_DIR=data
DIU_MAX_STORAGE_MB=50
```

---

## Verification & Testing

Execute the automated test suite covering all services, models, and endpoints:
```bash
python -m pytest -v
```

---

## Execution Options

### Option 1: Local MCP stdio Mode
Used for desktop applications such as Claude Desktop and Cursor IDE:
```bash
python server.py --transport stdio
```

### Option 2: Production REST API Mode
Used for ChatGPT Custom GPT Actions, web frontends, and cloud hosting:
```bash
python server.py --transport http --host 0.0.0.0 --port 8000
```
Interactive API documentation will be available at:
* Swagger UI: `http://localhost:8000/docs`
* OpenAPI Schema: `http://localhost:8000/openapi.json`
* Health Endpoint: `http://localhost:8000/health`
* MCP SSE Endpoint: `http://localhost:8000/mcp`

### Option 3: Docker Deployment
```bash
docker compose up -d --build
```

---

## Client Integration

### Claude Desktop Configuration
Add the server entry to your Claude Desktop config file:

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

### ChatGPT Actions Configuration
1. Run the server in HTTP mode on a public URL (e.g., using Render, Railway, or a tunnel).
2. Go to **Explore GPTs** $\to$ **Create a GPT** $\to$ **Configure**.
3. Under **Actions**, click **Create new action**.
4. Select **Import from URL** and paste: `https://your-server-domain/openapi.json`.
5. ChatGPT will automatically configure the endpoints for searching questions, reviewing text transcriptions, streaming diagrams, and downloading original papers.

---

## MCP Tools Reference (10 Tools)

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

## REST API Reference

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health status. |
| `GET` | `/docs` | Swagger interactive documentation. |
| `GET` | `/openapi.json` | OpenAPI 3.1 specification for ChatGPT Actions. |
| `GET` | `/api/departments` | Discovered department list. |
| `GET` | `/api/courses` | Department courses by query parameter. |
| `GET` | `/api/semesters` | Available semesters for a given course. |
| `GET` | `/api/exam-types` | Available exam categories for a given course. |
| `POST` | `/api/search` | Search papers without local disk storage. |
| `POST` | `/api/collect` | Collect papers and record database entries. |
| `GET` | `/api/files/{file_id}` | Retrieve metadata and question text. |
| `GET` | `/api/files/{file_id}/download` | Stream binary PDF directly to browser/client. |
| `GET` | `/api/files/{file_id}/pages/{page}` | **Stream page as PNG image for browser/vision AI.** |
| `GET` | `/api/collections/{id}` | Session collection summary. |

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
