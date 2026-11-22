# DIU Previous Question MCP Server

An interactive, production-ready [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) Server in Python that dynamically discovers, crawls, archives, and delivers original Daffodil International University (DIU) examination question PDFs from [OurDIU Question Bank](https://ourdiu.com/questions/browse) to AI agents (such as Claude, ChatGPT, Cursor, and custom MCP clients).

---

## 🚀 Key Highlights & Philosophy

* **100% Original PDF Preservation**: Strict binary download via HTTP. No OCR, no text extraction, no page rasterization, no compression, and no format conversion. All math equations, figures, tables, and exam layouts are preserved pixel-for-pixel.
* **Direct AI Document Delivery**: Exposes individual PDF documents using the official MCP binary resource mechanism (`types.BlobResourceContents` with MIME `application/pdf`) and MCP tools, avoiding bloated ZIP archives or lossy text transforms.
* **Dynamic Discovery (Zero Hardcoding)**: Automatically extracts departments, courses, course-specific semesters, and exam types from live OurDIU server state (React Router / Remix turbo-stream payload and HTML fallback).
* **Conversational AI Workflows**: Optimized tool schemas and descriptions designed for step-by-step interactive agent conversations:
  1. Department selection
  2. Course selection
  3. Semester selection (defaults to **all available semesters**, or supports single/multiple selections)
  4. Exam type selection (Midterm, Final, Quiz, or All)
* **Comprehensive Caching & Verification**: SQLite-backed metadata tracking, SHA-256 checksum computation, `%PDF-` binary magic header validation, and deduplication.

---

## 🏗️ Architecture

```
                                  +---------------------------------------+
                                  |         MCP Client (AI Agent)         |
                                  |   (Claude Desktop, Cursor, ChatGPT)   |
                                  +-------------------+-------------------+
                                                      |
                                           JSON-RPC (stdio / SSE)
                                                      |
                                  +-------------------v-------------------+
                                  |         DIU Question MCP Server       |
                                  |               (server.py)             |
                                  +---------+-------------------+---------+
                                            |                   |
                     +----------------------v-------+   +-------v----------------------+
                     |         MCP Tools &          |   |          SQLite Store        |
                     |      Resource Delivery       |   |  (departments, courses,      |
                     |  (diu-question://pdf/{id})   |   |   collections, sha256 cache) |
                     +--------------+---------------+   +------------------------------+
                                    |
                     +--------------v---------------+
                     |     Collection Coordinator   |
                     | (services/collection_service)|
                     +-------+--------------+-------+
                             |              |
           +-----------------v----+    +----v--------------------+
           |  Scraper & Crawler   |    |    Downloader Engine    |
           | - Departments/Courses|    | - HTTP Binary Download  |
           | - Semesters & Types  |    | - %PDF- Magic Header Val|
           | - Multi-page Crawl   |    | - SHA-256 Verification  |
           | - Submissions & URLs |    | - Local Storage Layout  |
           +-----------------+----+    +----+--------------------+
                             |              |
                             +-------+------+
                                     |
                                     v
                   +----------------------------------+
                   |       OurDIU Data Sources        |
                   | - ourdiu.com (React Router SSR)  |
                   | - files.ourdiu.com (PDF storage) |
                   +----------------------------------+
```

---

## 📁 Project Structure

```
diu-question/
├── server.py                 # Main MCP server entrypoint (stdio & sse transports)
├── config.py                 # Central configuration and environment settings
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Project packaging specification
├── .env.example              # Example environment variable template
├── .gitignore                # Git exclusions
├── README.md                 # Full documentation
├── test_live_integration.py  # Live end-to-end integration test against OurDIU
│
├── scraper/                  # Dynamic discovery & web crawling
│   ├── __init__.py
│   ├── client.py             # Async HTTP client & React Router stream parser
│   ├── departments.py        # Department discovery
│   ├── courses.py            # Course discovery & alias matching
│   ├── semesters.py          # Semester discovery & normalization logic
│   ├── exams.py              # Exam type normalization & filtering
│   ├── pagination.py         # Multi-page pagination traversal
│   └── pdf_extractor.py      # Exam detail page & submission PDF URL extraction
│
├── downloader/               # Original binary PDF downloading & storage
│   ├── __init__.py
│   ├── pdf_downloader.py     # Resilient async HTTP PDF downloader
│   ├── validator.py          # %PDF- header, size, & SHA-256 validation
│   └── storage.py            # Local directory layout & filename sanitization
│
├── database/                 # SQLite metadata persistence & cache
│   ├── __init__.py
│   ├── models.py             # Dataclasses & Pydantic models
│   └── repository.py         # SQLite database operations & indexing
│
├── services/                 # Business logic and coordination
│   ├── __init__.py
│   ├── collection_service.py # End-to-end collection workflow coordinator
│   ├── cache_service.py      # Cache lookup & disk verification
│   └── metadata_service.py   # Summary statistics & byte formatting
│
├── tests/                    # Comprehensive automated test suite
│   ├── test_scraper.py       # Scraper & stream decoder unit tests
│   ├── test_downloader.py    # PDF validator & storage tests
│   ├── test_filters.py       # Semester & exam type normalization tests
│   └── test_mcp.py           # MCP tool invocation & resource delivery tests
│
└── data/                     # Local question PDF repository (organized by course)
    ├── .gitkeep
    └── diu_questions.db      # SQLite database
```

---

## 📦 System Requirements

* **Python 3.11+** (Tested and fully compatible with Python 3.11, 3.12, 3.13, and 3.14).
* **Operating System**: Windows 10/11, macOS, or Linux.
* **Network Access**: Outbound HTTPS to `ourdiu.com` and `files.ourdiu.com`.

---

## ⚙️ Installation & Setup

### 1. Clone or Open the Repository
```bash
cd c:\Users\tasin\Downloads\diu-question
```

### 2. Set Up a Python Virtual Environment

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

*(Optional development tools)*:
```bash
pip install pytest pytest-asyncio
```

### 4. Configure Environment
Copy the example environment configuration:
```powershell
Copy-Item .env.example .env
```

---

## 🧪 Running the Tests

Execute the automated test suite (25 unit tests covering scrapers, filters, pagination, downloader, and MCP tools):
```powershell
python -m pytest -v
```

Run the live integration test (crawls and downloads actual question papers from OurDIU to verify live website compatibility):
```powershell
python test_live_integration.py
```

---

## 🌐 Universal Multi-Platform Deployment (Claude, ChatGPT, Docker & Cloud)

This server is built with a **Universal Hybrid Architecture**:
1. **Local MCP Mode (`stdio`)**: For Claude Desktop, Cursor IDE, VS Code.
2. **Production REST API & OpenAPI 3.1 Mode (`http`)**: For **ChatGPT (Custom GPT Actions)**, Web Apps, Mobile Apps, and Cloud Deployments.
3. **Remote MCP Mode (`sse`)**: For remote Claude / LibreChat / Dify integrations.

---

### 🐳 1. Docker Deployment (Production-Ready)

Run the server anywhere with a single Docker command:

```bash
docker compose up -d
```

Or build manually:
```bash
docker build -t diu-question-server .
docker run -d -p 8000:8000 -v diu_data:/app/data --name diu-server diu-question-server
```

* **Swagger UI Documentation**: `http://localhost:8000/docs`
* **OpenAPI 3.1 Schema**: `http://localhost:8000/openapi.json`
* **Health Check**: `http://localhost:8000/health`
* **MCP SSE Endpoint**: `http://localhost:8000/mcp`

---

### 🤖 2. Connecting to ChatGPT (Web, Desktop, & Mobile)

ChatGPT uses standard **OpenAPI 3.0/3.1 Actions** to interact with external tools:

1. Start the server in HTTP mode:
   ```bash
   python server.py --transport http --port 8000
   ```
2. If running locally, expose it via a tunnel:
   ```bash
   npx localtunnel --port 8000
   # Or using Cloudflare / ngrok:
   # ngrok http 8000
   ```
3. Open [chatgpt.com](https://chatgpt.com) $\to$ **Explore GPTs** $\to$ **Create a GPT**.
4. In the **Configure** tab:
   * **Name**: DIU Question Solver
   * Scroll down to **Actions** $\to$ Click **Create new action**.
   * Under **Schema**, paste the content from your server's `/openapi.json` (or import from your public URL: `https://your-domain.com/openapi.json`).
5. Save the GPT!
   * Now, **ChatGPT on web, desktop, and mobile (iOS & Android)** can search, download, and analyze DIU previous exam questions directly!

---

### ☁️ 3. Deploying to Cloud Platforms

#### Option A: Render (Free / Web Service)
1. Fork or push this repository to GitHub.
2. In [Render Dashboard](https://dashboard.render.com), click **New Web Service** $\to$ Connect your repo.
3. Select **Docker** environment (or Python environment with start command: `uvicorn api:app --host 0.0.0.0 --port $PORT`).
4. Add a Persistent Disk mounted at `/app/data` to cache downloaded PDFs.

#### Option B: Railway / Fly.io
```bash
# Fly.io
fly launch
fly deploy

# Railway
railway up
```

---

## 🚀 Running the MCP Server

### Mode 1: Standard Stdio Transport (Recommended for Claude Desktop & Cursor)
```bash
python server.py --transport stdio
```

### Mode 2: SSE / HTTP Transport (For remote AI clients or network access)
```bash
python server.py --transport sse --host 127.0.0.1 --port 8000
```
* The SSE endpoint will be available at: `http://127.0.0.1:8000/sse`

---

## 🔌 Connecting to MCP Clients

### Connecting to Claude Desktop

Edit your Claude Desktop configuration file:
* **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
* **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the `diu-question-mcp` server:

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
      "env": {
        "DIU_DATA_DIR": "c:\\Users\\tasin\\Downloads\\diu-question\\data",
        "DIU_DB_PATH": "c:\\Users\\tasin\\Downloads\\diu-question\\data\\diu_questions.db"
      }
    }
  }
}
```

> **Windows Tip**: Use double backslashes (`\\`) in JSON file paths, or point to your virtual environment's Python executable (e.g., `C:\\Users\\tasin\\Downloads\\diu-question\\.venv\\Scripts\\python.exe`).

### Connecting to Cursor IDE

1. Open **Cursor Settings** -> **Features** -> **MCP**.
2. Click **+ Add New MCP Server**.
3. Fill in the fields:
   * **Name**: `diu-question`
   * **Type**: `command`
   * **Command**: `python c:\Users\tasin\Downloads\diu-question\server.py --transport stdio`

---

## 💬 Interactive User Experience

The MCP tools are annotated to encourage conversational agent workflows:

````markdown
User: "Can you help me find previous exam questions from DIU?"

Agent: "I can help with that! Which department are you looking for? (e.g. CSE, EEE, BBA, Civil, English, etc.)"
[Agent calls `list_departments()` to check available departments]

User: "CSE"

Agent: "Which course in Computer Science and Engineering do you need questions for?"
[Agent calls `list_courses(department="CSE")`]

User: "Operating Systems" (or "CSE 221")

Agent: "For Operating Systems, previous questions are available across multiple semesters:
- Fall 26
- Spring 26
- Fall 25
- Summer 25
- Fall 24
- Spring 24
- Fall 23

Which semester(s) would you like? (By default, I can collect All semesters, or specific ones like 'Fall 2024')."

User: "Fall 2024 and Fall 26"

Agent: "Got it. Which exam types do you need?
1. Midterm
2. Final
3. Quiz
4. All exam types"

User: "Midterm and Final"

Agent: [Agent calls `collect_questions(department="CSE", course="Operating Systems", semesters=["Fall 2024", "Fall 2026"], exam_types=["midterm", "final"])`]

Agent: "I have collected 7 question papers for Operating Systems across Fall 26 and Fall 24 (total size: 1.84 MB).
Here is the summary of downloaded papers:
- Fall 26 Midterm (Section B, Section M)
- Fall 24 Final
- Fall 24 Midterm

Would you like me to inspect any of these exam papers?"
````

---

## 🛠️ MCP Tools Reference

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `list_departments` | `force_refresh: bool = False` | Returns all academic departments discovered from OurDIU. |
| `list_courses` | `department: str, force_refresh: bool = False` | Returns all courses under the given department (supports short name, full name, or ID). |
| `list_semesters` | `department: str, course: str` | Returns semesters specifically containing examination papers for the selected course. |
| `list_exam_types` | `department: str, course: str` | Returns available exam categories for the course (Midterm, Final, Quiz). |
| `search_questions` | `department, course, semesters="all", exam_types="all"` | Crawls exam entries and extracts PDF candidates **without downloading**, useful for previewing. |
| `collect_questions` | `department, course, semesters="all", exam_types="all", force_refresh=False` | Downloads original PDFs, validates binary integrity, stores to disk, records metadata, and returns a summary. |
| `list_collected_files`| `bundle_id: Optional[str] = None` | Lists metadata and unique `file_id`s for collected PDF documents. |
| `get_pdf_file` | `file_id: str` | Returns one individual original PDF through an embedded MCP `BlobResourceContents` (MIME `application/pdf`) and local disk path. |
| `get_question_collection_summary` | `collection_id: str` | Returns detailed statistics (total files, size, distributions) for a previous collection session. |

---

## 📄 MCP Resource URIs

* **`diu-question://pdf/{file_id}`**: Delivers the unmodified binary PDF data (`application/pdf`) encoded in base64.
* **`diu-question://collection/{collection_id}`**: Delivers collection session metadata as formatted JSON.

---

## 📑 Local PDF Storage Layout

Original PDF files are organized predictably on disk:

```
data/
└── CSE/
    └── Operating_Systems/
        ├── Fall_26/
        │   └── quiz/
        │       ├── question_1949_sub_2967_sec_m.pdf
        │       ├── question_1949_sub_3208_sec_B.pdf
        │       ├── question_1949_sub_3210_sec_66-J.pdf
        │       ├── question_1949_sub_3211_sec_66-B.pdf
        │       └── question_1949_sub_3212_sec_J.pdf
        └── Fall_24/
            ├── final/
            │   └── question_1230_sub_1800.pdf
            └── midterm/
                └── question_1226_sub_1795.pdf
```

---

## 🔍 Understanding LLM PDF Delivery & Limitations

### 1. Exposing vs. Retrieving vs. Attaching
* **Exposing a PDF through MCP**: The MCP server registers resources with URI `diu-question://pdf/{file_id}` and tools returning `types.BlobResourceContents(blob=..., mime_type="application/pdf")`.
* **Client Retrieval**: When an AI client invokes `get_pdf_file(file_id)`, the MCP host receives the response containing both the local absolute file path and the base64 binary blob.
* **Client Attachment to LLM Context**:
  * **Native PDF Understanding (e.g., Claude 3.5 Sonnet / Gemini 1.5 Pro)**: If the client host application supports binary attachments, it forwards the PDF bytes directly to the model's multimodal document understanding pipeline.
  * **Clients without direct binary MCP ingestion**: For clients that do not automatically inject binary MCP tool returns into LLM context, `get_pdf_file` returns the canonical `local_path` on disk. The client or user can directly access or attach the file from disk.

### 2. Why No OCR or Text Extraction?
University examination questions in computer science, engineering, and mathematics frequently include circuit diagrams, graphs, UML diagrams, tree structures, mathematical equations, and formatted code snippets. Rasterizing or running basic OCR on these files degrades fidelity. By preserving the original vector PDF bytes, modern multimodal LLMs can inspect the original document directly without loss of structure.

---

## 🛡️ Error Handling & Resilience

* **Rate Limiting & Politeness**: Scraper introduces polite inter-request delays and respects HTTP 429 `Retry-After` headers.
* **Exponential Backoff**: Up to 3 retries on transient network disconnects or 5xx gateway drops.
* **Binary Magic Header Verification**: Validates `b'%PDF-'` on all downloads to avoid saving HTML error pages as `.pdf`.
* **Deduplication**: Files with matching SHA-256 hashes are not redownloaded unless `force_refresh=True` is provided.

---

## 📜 License

MIT License. Designed for academic and educational question paper retrieval.
