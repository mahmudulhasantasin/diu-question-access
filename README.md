# DIU Question Access — Production MCP & REST Server

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![MCP Specification](https://img.shields.io/badge/MCP-Protocol%20v2.3-purple.svg)](https://modelcontextprotocol.io/)
[![Framework](https://img.shields.io/badge/FastAPI-0.139-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Build & Tests](https://img.shields.io/badge/Tests-31%20Passed-success.svg)]()

An enterprise-grade, universal **Model Context Protocol (MCP)** and **REST API** server that dynamically discovers, crawls, archives, and delivers original Daffodil International University (DIU) examination question papers from the [OurDIU Question Bank](https://ourdiu.com/questions/browse).

Built for seamless integration with **Claude Desktop, ChatGPT (Custom GPT Actions), Cursor IDE, VS Code, and any Cloud platform (Koyeb, Render, Docker, VPS)**.

---

## 📑 Table of Contents

- [Key Architectural Highlights](#-key-architectural-highlights)
- [System Architecture](#-system-architecture)
- [Project Directory Layout](#-project-directory-layout)
- [Requirements](#-requirements)
- [Local Installation & Setup](#-local-installation--setup)
- [Running Automated Tests](#-running-automated-tests)
- [Execution Modes](#-execution-modes)
- [Client Integration Guides](#-client-integration-guides)
  - [1. Claude Desktop Setup](#1-claude-desktop-setup)
  - [2. ChatGPT Setup (Web, Desktop & Mobile)](#2-chatgpt-setup-web-desktop--mobile)
  - [3. Cursor IDE Setup](#3-cursor-ide-setup)
  - [4. MCP Inspector (Visual Testing)](#4-mcp-inspector-visual-testing)
- [Interactive Conversational Workflow](#-interactive-conversational-workflow)
- [MCP Tools Reference (9 Tools)](#-mcp-tools-reference-9-tools)
- [REST API Endpoints Reference](#-rest-api-endpoints-reference)
- [Cloud Deployment (Koyeb, Render, Docker)](#-cloud-deployment-koyeb-render-docker)
- [Storage Layout & Deduplication](#-storage-layout--deduplication)
- [Troubleshooting & FAQs](#-troubleshooting--faqs)
- [License](#-license)

---

## 🌟 Key Architectural Highlights

* **100% Original PDF Preservation**: Strict binary download via HTTP. No lossy OCR, no text extraction pipelines, no rasterization to images, and no compression. All mathematical formulas, circuit schematics, UML diagrams, algorithms, and formatting remain 100% intact.
* **Universal Multi-Platform Delivery**:
  * **Local stdio Transport**: For Claude Desktop, Cursor IDE, Windsurf, and VS Code.
  * **OpenAPI 3.1 & REST API**: For ChatGPT Custom GPT Actions, Mobile apps, and Web applications.
  * **Streamable SSE Transport**: For remote MCP hosts (Claude.ai Web Connectors, LibreChat, Dify).
* **Dynamic Discovery (Zero Hardcoding)**: Automatically extracts departments, courses (with aliases like `os`, `ds`, `algo`), semesters, and exam types from live OurDIU server state (React Router / Remix turbo-stream payload and HTML fallback).
* **Safe Large-File Delivery**: Provides official question text transcriptions directly in tool responses to prevent client IPC buffer crashes on large PDFs, while serving direct download links and local paths.
* **High-Performance Caching & SQLite Repository**: Indexed SQLite storage tracking SHA-256 hashes, file sizes, and metadata to prevent redundant downloads.

---

## 🏗️ System Architecture

```
                             +-------------------------------------------------------------+
                             |                         AI Clients                          |
                             |   Claude Desktop | ChatGPT (GPT-4o) | Cursor IDE | Web App  |
                             +--------------+------------------------------+---------------+
                                            |                              |
                             JSON-RPC (stdio)                      HTTP / REST / SSE
                                            |                              |
                             +--------------v------------------------------v---------------+
                             |              DIU Question Universal Server                  |
                             |                (server.py / api.py)                         |
                             +-----------------------------+-------------------------------+
                                                           |
                      +------------------------------------+-----------------------------------+
                      |                                                                        |
     +----------------v----------------+                                      +----------------v----------------+
     |        MCP Tools Engine         |                                      |        FastAPI REST API         |
     | - list_departments              |                                      | - GET  /health                  |
     | - list_courses                  |                                      | - GET  /openapi.json            |
     | - list_semesters                |                                      | - GET  /docs (Swagger UI)       |
     | - list_exam_types               |                                      | - POST /api/search              |
     | - search_questions              |                                      | - POST /api/collect             |
     | - collect_questions             |                                      | - GET  /api/files/{id}/download |
     | - get_pdf_file                  |                                      +----------------+----------------+
     +----------------+----------------+                                                       |
                      |                                                                        |
                      +------------------------------------+-----------------------------------+
                                                           |
                                            +--------------v---------------+
                                            |     Collection Coordinator   |
                                            | (services/collection_service)|
                                            +-------+--------------+-------+
                                                    |              |
                                  +-----------------v----+    +----v--------------------+
                                  |   Crawler Engine     |    |    Downloader Engine    |
                                  | - Turbo-stream Parser|    | - HTTP Binary Download  |
                                  | - Multi-page Crawl   |    | - %PDF- Magic Header Val|
                                  | - Submissions & URLs |    | - SHA-256 Verification  |
                                  | - Aliases & Semesters|    | - SQLite Deduplication  |
                                  +-----------------+----+    +----+--------------------+
                                                    |              |
                                                    +-------+------+
                                                            |
                                                            v
                                          +----------------------------------+
                                          |       OurDIU Data Sources        |
                                          | - ourdiu.com (React Router SSR)  |
                                          | - files.ourdiu.com (Original PDF)|
                                          +----------------------------------+
```

---

## 📁 Project Directory Layout

```
diu-question/
├── api.py                    # Production FastAPI REST API & OpenAPI 3.1 server
├── server.py                 # Multi-transport server entrypoint (stdio, http, sse)
├── config.py                 # Global configurations & environment variable loader
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Build metadata & pytest configuration
├── Dockerfile                # Production multi-stage Docker container specification
├── docker-compose.yml        # Docker compose configuration with persistent volume
├── test_live_integration.py  # End-to-end integration test against live OurDIU site
├── README.md                 # Complete system documentation
├── .env.example              # Environment variables template
├── .gitignore                # Git exclusions
│
├── scraper/                  # Web scraping & dynamic discovery
│   ├── client.py             # Async HTTP client with retry logic & turbo-stream decoder
│   ├── departments.py        # Department discovery
│   ├── courses.py            # Course discovery & alias matching
│   ├── semesters.py          # Semester discovery & normalization logic
│   ├── exams.py              # Exam type normalization & filtering
│   ├── pagination.py         # Multi-page pagination traversal
│   └── pdf_extractor.py      # Detail page parser & multi-submission extraction
│
├── downloader/               # PDF download, validation & storage
│   ├── pdf_downloader.py     # Resilient async HTTP binary downloader
│   ├── validator.py          # %PDF- header, size, and SHA-256 checksum validator
│   └── storage.py            # Sanitized local directory management
│
├── database/                 # SQLite metadata persistence & cache
│   ├── models.py             # Dataclasses & Pydantic models
│   └── repository.py         # SQLite database operations & indexing
│
├── services/                 # Business logic and coordination
│   ├── collection_service.py # Core collection workflow coordinator
│   ├── cache_service.py      # Cache lookup & disk verification
│   └── metadata_service.py   # Statistical summaries & formatting
│
├── tests/                    # Automated test suite (31 unit tests)
│   ├── test_api.py           # FastAPI REST & OpenAPI endpoint tests
│   ├── test_scraper.py       # Scraper & stream decoder tests
│   ├── test_downloader.py    # PDF validator & storage tests
│   ├── test_filters.py       # Semester & exam type normalization tests
│   └── test_mcp.py           # MCP tool invocation & resource delivery tests
│
└── data/                     # Local question PDF repository
    ├── diu_questions.db      # SQLite database
    └── CSE/Operating_Systems/...
```

---

## 💻 Requirements

* **Python**: `3.11` or higher (fully tested on Python 3.11, 3.12, 3.13, and 3.14).
* **Operating Systems**: Windows 10/11, macOS, or Linux.
* **Network Access**: Outbound HTTPS to `ourdiu.com` and `files.ourdiu.com`.

---

## 🚀 Local Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/mahmudulhasantasin/diu-question-access.git
cd diu-question-access
```

### 2. Set Up a Virtual Environment

#### On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Local Environment Configuration
```powershell
Copy-Item .env.example .env
```

---

## 🧪 Running Automated Tests

Run the complete automated test suite (31 unit tests covering all components):
```bash
python -m pytest -v
```

Run the live integration test (crawls and downloads actual question papers from OurDIU to verify live website connectivity):
```bash
python test_live_integration.py
```

---

## ⚡ Execution Modes

### Mode 1: Local MCP stdio (For Claude Desktop & Cursor)
```bash
python server.py --transport stdio
```

### Mode 2: Production REST API & Swagger UI (For ChatGPT & Cloud)
```bash
python server.py --transport http --host 0.0.0.0 --port 8000
```
* **Swagger UI Documentation**: `http://localhost:8000/docs`
* **OpenAPI 3.1 Specification**: `http://localhost:8000/openapi.json`
* **Health Check**: `http://localhost:8000/health`
* **MCP SSE Endpoint**: `http://localhost:8000/mcp`

### Mode 3: Docker Container
```bash
docker compose up -d
```

---

## 🔌 Client Integration Guides

### 1. Claude Desktop Setup

1. Open your Claude Desktop configuration file:
   * **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
     *(Or if your Claude profile uses `AppData\Local\Claude-Data\<profile>\claude_desktop_config.json`)*
   * **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Add the `diu-question` configuration:
```json
{
  "mcpServers": {
    "diu-question": {
      "command": "C:\\Users\\tasin\\AppData\\Local\\Programs\\Python\\Python314\\python.exe",
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

3. Completely quit Claude Desktop (Right-click in System Tray $\to$ **Quit**) and relaunch.
4. Go to **Settings $\to$ Developer / Plugins**; `diu-question` will show as **Active**.

---

### 2. ChatGPT Setup (Web, Desktop & Mobile)

ChatGPT interacts with external servers using **OpenAPI Actions**:

1. Start your server in HTTP mode:
   ```bash
   python server.py --transport http --port 8000
   ```
2. If running locally, expose your server with a public HTTPS URL:
   ```bash
   npx localtunnel --port 8000
   # Or: ngrok http 8000
   ```
   *(If hosted on Koyeb or Render, use your permanent URL, e.g. `https://your-app.koyeb.app`)*.

3. Open [chatgpt.com](https://chatgpt.com) $\to$ **Explore GPTs** $\to$ **Create a GPT**.
4. In the **Configure** tab:
   * Name: `DIU Question Helper`
   * Under **Actions**, click **Create new action**.
   * Under **Schema**, paste the contents of your `/openapi.json` URL (or click **Import from URL** and enter `https://your-app.koyeb.app/openapi.json`).
5. Save the GPT.
6. Now, on **any device (Web, Desktop, iOS, Android)**, ask ChatGPT:
   > *"Show me previous exam questions for Operating Systems at DIU CSE."*  
   ChatGPT will call your server, fetch the questions, and provide full summaries!

---

### 3. Cursor IDE Setup

1. Open **Cursor Settings** $\to$ **Features** $\to$ **MCP**.
2. Click **+ Add New MCP Server**:
   * **Name**: `diu-question`
   * **Type**: `command`
   * **Command**: `python c:\Users\tasin\Downloads\diu-question\server.py --transport stdio`

---

### 4. MCP Inspector (Visual Testing)

To test every tool and inspect responses directly inside a web browser UI without any AI client:
```bash
npx @modelcontextprotocol/inspector python server.py
```
Open the generated localhost URL to test `list_departments`, `list_courses`, `collect_questions`, etc.

---

## 💬 Interactive Conversational Workflow

```markdown
User: "Find previous questions for Operating Systems from DIU CSE."

Agent: [Calls `list_semesters(department="CSE", course="Operating Systems")`]
Agent: "For Operating Systems, questions are available for:
- Fall 26
- Spring 26
- Fall 25
- Summer 25
- Fall 24
- Spring 24
- Fall 23

Which semesters would you like? (By default, I can collect 'All', or specific ones like 'Fall 2024')."

User: "Fall 26 Midterm and Quiz"

Agent: [Calls `collect_questions(department="CSE", course="Operating Systems", semesters="Fall 26", exam_types=["midterm", "quiz"])`]

Agent: "I have collected 10 question papers for Fall 26 (5 Midterm, 5 Quiz).
Total download size: 3.37 MB.
Would you like me to inspect and analyze the questions?"

User: "Analyze the Midterm questions and tell me the main topics."

Agent: [Calls `get_pdf_file(file_id="pdf_1996_2999")`]
Agent: "Here is the breakdown of the Fall 26 Midterm Exam for Operating Systems:
1. Process Management: Process lifecycle, fork() behavior, child-parent synchronization.
2. CPU Scheduling: Gantt chart calculations for Round Robin and SJF.
3. Concurrency & Deadlocks: Four conditions of deadlock, Banker's algorithm.

Download original PDF: https://files.ourdiu.com/watermarked/dd975da1-3a98-482d-af7f-3f6d3bfe2b1b.pdf
Saved locally at: data/CSE/Operating_Systems/Fall_26/midterm/question_1996_sub_2999_sec_L.pdf"
```

---

## 🛠️ MCP Tools Reference (9 Tools)

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `list_departments` | `force_refresh: bool = False` | Returns all academic departments discovered from OurDIU. |
| `list_courses` | `department: str, force_refresh: bool = False` | Returns all courses under the given department (supports short name, full name, or ID). |
| `list_semesters` | `department: str, course: str` | Returns semesters specifically containing question papers for the selected course. |
| `list_exam_types` | `department: str, course: str` | Returns available exam categories for the course (Midterm, Final, Quiz). |
| `search_questions` | `department, course, semesters="all", exam_types="all"` | Crawls exam entries and extracts PDF candidates **without downloading** (preview mode). |
| `collect_questions` | `department, course, semesters="all", exam_types="all", force_refresh=False` | Downloads original PDFs, validates binary integrity, stores to disk, records metadata, and returns a summary. |
| `list_collected_files`| `bundle_id: Optional[str] = None` | Lists metadata and unique `file_id`s for collected PDF documents. |
| `get_pdf_file` | `file_id: str` | Returns question paper transcription, direct download link, local disk path, and binary resource reference. |
| `get_question_collection_summary` | `collection_id: str` | Returns detailed statistics (total files, size, distributions) for a previous collection session. |

---

## 🌐 REST API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Container & orchestrator health check. |
| `GET` | `/docs` | Interactive Swagger UI documentation. |
| `GET` | `/openapi.json` | OpenAPI 3.1 specification for ChatGPT Actions. |
| `GET` | `/api/departments` | Discovered departments list. |
| `GET` | `/api/courses?department=CSE` | Department course list. |
| `GET` | `/api/semesters?department=CSE&course=Operating+Systems` | Course-specific semesters list. |
| `GET` | `/api/exam-types?department=CSE&course=Operating+Systems`| Available exam types list. |
| `POST`| `/api/search` | Search exam entries without downloading. |
| `POST`| `/api/collect` | Download matching PDFs and record metadata. |
| `GET` | `/api/files?bundle_id={id}` | List collected files. |
| `GET` | `/api/files/{file_id}` | Retrieve file metadata & question transcription. |
| `GET` | `/api/files/{file_id}/download` | Direct binary PDF streaming & browser download. |
| `GET` | `/api/collections/{collection_id}` | Collection bundle summary statistics. |

---

## ☁️ Cloud Deployment (Koyeb, Render, Docker)

### Deploying to Koyeb (Free, Always-On, No Sleep)
1. Sign up for free at [koyeb.com](https://www.koyeb.com/) using GitHub.
2. Click **Create App** $\to$ Select **GitHub**.
3. Select your repository `mahmudulhasantasin/diu-question-access`.
4. Koyeb automatically detects `Dockerfile`.
   * **Instance**: `Free (Nano)`
   * **Port**: `8000`
5. Click **Deploy**. Your permanent HTTPS URL will be ready in under 2 minutes!

### Deploying to Render
1. Go to [render.com](https://render.com/) $\to$ **New Web Service**.
2. Connect your repository.
3. Configure:
   * **Environment**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
4. Deploy!

---

## 🗄️ Storage Layout & Deduplication

Downloaded PDFs are saved locally in a structured hierarchy:

```
data/
├── diu_questions.db          # SQLite metadata, checksums, and collection records
└── CSE/
    └── Operating_Systems/
        ├── Fall_26/
        │   ├── midterm/
        │   │   ├── question_1996_sub_2998_sec_B.pdf
        │   │   └── question_1996_sub_2999_sec_L.pdf
        │   └── quiz/
        │       ├── question_1949_sub_2967_sec_m.pdf
        │       └── question_1949_sub_3211_sec_66-B.pdf
        └── Fall_24/
            ├── final/
            │   └── question_1230_sub_1800.pdf
            └── midterm/
                └── question_1226_sub_1795.pdf
```

---

## ❓ Troubleshooting & FAQs

#### Q: Claude says "get_pdf_file error" or "cannot open path from my workspace"?
**A**: This occurs when an AI client running in the cloud tries to access a local Windows drive path (`C:\...`) or when large base64 buffers exceed client limits. We solved this by delivering the official question transcription directly inside `question_text` and providing direct download links (`pdf_download_url`).

#### Q: Does this server perform OCR or modify the PDFs?
**A**: No. Per project specifications, the original PDF bytes are downloaded directly via HTTP and verified using magic bytes `%PDF-` and SHA-256 checksums. No OCR, text chunking, embedding, or conversion is performed.

#### Q: How do I force redownload of already cached papers?
**A**: Pass `force_refresh=True` to the `collect_questions` tool or `/api/collect` REST endpoint.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE). Developed for academic reference and student research.
