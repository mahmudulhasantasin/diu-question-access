# DIU Question Access — Production MCP & REST Server

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![MCP Specification](https://img.shields.io/badge/MCP-Protocol%20v2.3-purple.svg)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Render-Deployed%20Live-brightgreen.svg?logo=render)](https://diu-question-access.onrender.com)
[![Tests](https://img.shields.io/badge/Tests-38%20Passed-success.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A high-performance **Model Context Protocol (MCP)** and **FastAPI REST API** server that dynamically discovers, indexes, streams, and delivers Daffodil International University (DIU) examination question papers from the OurDIU repository.

Engineered with a **Dual-Protocol Engine** for universal compatibility across:
- **Google Gemini** (Connected Apps via Streamable HTTP JSON-RPC)
- **OpenAI ChatGPT** (Custom MCP Plugin via SSE & Custom GPT Actions via OpenAPI)
- **Claude Desktop, Cursor, Windsurf** (SSE & stdio)
- **Web Browsers & Mobile Clients** (Interactive Swagger UI & REST APIs)

---

## 🌐 Live Service Endpoints

The server is deployed live on cloud infrastructure:

| Endpoint | URL | Description |
| :--- | :--- | :--- |
| **Primary Root** | [https://diu-question-access.onrender.com/](https://diu-question-access.onrender.com/) | Live status & index summary |
| **Universal MCP Endpoint** | `https://diu-question-access.onrender.com/mcp` | Dual-mode MCP: SSE (GET) & JSON-RPC (POST) |
| **Interactive Docs** | [https://diu-question-access.onrender.com/docs](https://diu-question-access.onrender.com/docs) | Interactive Swagger UI (test in browser) |
| **OpenAPI Specification** | [https://diu-question-access.onrender.com/openapi.json](https://diu-question-access.onrender.com/openapi.json) | OpenAPI 3.1 schema for ChatGPT Actions |
| **Health Check** | [https://diu-question-access.onrender.com/health](https://diu-question-access.onrender.com/health) | Uptime and database health probe |

> [!NOTE]
> **Free Tier Cold Starts**: Render spins down inactive instances. The very first request after inactivity may take ~30–50 seconds to wake up. Subsequent requests respond instantly.

---

## 📖 How to Use (Integration Guide)

### 1. Connect to Google Gemini (Connected Apps / Custom MCP)

Google Gemini natively supports connecting to custom MCP servers via Streamable HTTP:

1. Open **[Google Gemini](https://gemini.google.com)** in your browser.
2. Click on **Settings** (or the **Tools / Extensions / Connected Apps** icon) $\to$ Select **Connect to an MCP server**.
3. In the dialog, enter the **MCP server URL**:
   ```text
   https://diu-question-access.onrender.com/mcp
   ```
4. Click **Next** / **Connect**. *(No authentication required — leave settings as default)*.
5. Gemini will automatically discover all 10 tools (`collect_questions`, `search_questions`, `list_departments`, `list_courses`, `preview_question_page`, etc.).
6. Ask Gemini directly in the chat:
   * *"DIU CSE ডিপার্টমেন্টের Art of Living কোর্সের Final পরীক্ষার প্রশ্নপত্রগুলো দাও"*
   * *"Show me previous Midterm questions for Operating Systems at DIU"*

---

### 2. Connect to ChatGPT as a Custom MCP Plugin

ChatGPT supports MCP servers via Server-Sent Events (SSE):

1. Open **[ChatGPT](https://chatgpt.com)** in your browser.
2. Go to **Plugins** / **Developer Settings** $\to$ Click **Add custom MCP server**.
3. Fill in the connection form:
   * **Name**: `DIU Question Access`
   * **Description**: `Search and retrieve DIU examination question papers with page previews.`
   * **Connection**: Select **Server URL**
   * **Server URL**: `https://diu-question-access.onrender.com/mcp`
   * **Authentication**: Select **No authentication** (None)
4. Check the confirmation box: ☑️ *"I understand and want to continue"*.
5. Click **Create as a plugin**.
6. The plugin will be created and activated immediately.

---

### 3. Connect to ChatGPT as a Custom GPT (Actions)

If you prefer building a dedicated **Custom GPT** with full control over system instructions:

1. In ChatGPT, navigate to **Explore GPTs** $\to$ Click **+ Create** $\to$ Select **Configure**.
2. Configure general info:
   * **Name**: `DIU Exam Assistant`
   * **Description**: `Search, transcribe, and preview past Daffodil International University question papers.`
3. Scroll down to **Actions** $\to$ Click **Create new action**.
4. In the **Import from URL** input, paste:
   ```text
   https://diu-question-access.onrender.com/openapi.json
   ```
5. Click **Import**. ChatGPT will auto-populate all endpoints.
6. Set **Authentication**: `None`.
7. Set **Privacy Policy**: `https://ourdiu.com`
8. In the **Instructions** box, paste:
   > "You are an academic assistant for Daffodil International University (DIU) students. Use the DIU Question actions to search past question papers by department, course, and semester. Transcribe questions clearly, provide high-resolution page previews when diagrams or formulas are discussed, and share direct download links."
9. Click **Save** (or **Publish**).

---

### 4. Connect to Claude Desktop

Connect Claude Desktop to the cloud service via SSE or run locally via `stdio`:

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

### 5. Direct Browser Usage (Interactive Swagger UI)

You can explore and test all endpoints directly without any AI client:

1. Visit: [https://diu-question-access.onrender.com/docs](https://diu-question-access.onrender.com/docs)
2. Click on any endpoint (e.g., `GET /api/departments` or `GET /api/courses`).
3. Click **Try it out** $\to$ Enter parameters $\to$ Click **Execute**.
4. View JSON data or rendered page images directly in your browser.

---

## 💬 Example Prompts to Try

Once connected to Gemini, ChatGPT, or Claude, try asking:

### 1. ডিপার্টমেন্ট ও কোর্সের প্রশ্ন খোঁজা (Department & Course Exploration)
* *"DIU তে কী কী ডিপার্টমেন্টের প্রশ্নব্যাংক আছে?"*
* *"Show all courses under the Computer Science and Engineering (CSE) department."*

### 2. সেমিস্টার ও পরীক্ষা অনুযায়ী প্রশ্ন বের করা (Finding Exam Papers)
* *"CSE ডিপার্টমেন্টের Art of Living কোর্সের Final পরীক্ষার সবগুলো প্রশ্ন দাও"*
* *"Find previous Midterm exam questions for Operating Systems from Fall 2023 and Spring 2024."*
* *"Are there any Final exam papers for 'Algorithms' in the Software Engineering department?"*

### 3. ডায়াগ্রাম ও ছবির পেজ প্রিভিউ (Multimodal Vision Analysis)
* *"Database Systems পরীক্ষার প্রশ্নপত্রের ১ নম্বর পেজটি প্রিভিউ করে ER ডায়াগ্রামটি বিশ্লেষণ কর।"*
* *"Show me the schematic or circuit diagram from question 3 of the Digital Logic Design exam paper."*
*(The server renders the exact PDF page as a high-resolution PNG image on-the-fly, allowing vision AI to analyze circuits, flowcharts, math equations, and tables).*

### 4. পরীক্ষার প্রস্তুতি ও সাজেশন (Exam Preparation & Analysis)
* *"Artificial Intelligence কোর্সের বিগত ৩টি সেমিস্টারের প্রশ্ন বিশ্লেষণ করে সবচেয়ে কমন টপিকগুলো বের কর।"*
* *"Compiler Design পরীক্ষার Midterm প্রশ্নের ভিত্তিতে একটি প্র্যাকটিস কুইজ তৈরি করে দাও।"*

### 5. সরাসরি PDF ডাউনলোড লিংক (Direct Download Links)
* *"Spring 2024 Object Oriented Programming Final পরীক্ষার অরিজিনাল PDF ডাউনলোড লিংক দাও।"*

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
| `GET` | `/mcp` | MCP Server-Sent Events (SSE) streaming endpoint (ChatGPT/Claude). |
| `POST` | `/mcp` | MCP Streamable HTTP JSON-RPC endpoint (Gemini). |
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

### 2. Automated Tests (38 Tests Passing 100%)
```bash
python -m pytest -v
```

### 3. Run Locally
```bash
# REST API & MCP HTTP Server (Port 8000)
python server.py --transport http --host 0.0.0.0 --port 8000

# stdio mode (Claude Desktop)
python server.py --transport stdio
```

---

## ⚖️ Disclaimer & Attribution

### 1. Attribution & Source Credits
This project programmatically indexes public examination question papers collected and archived by the student community at **[OurDIU](https://ourdiu.com/)**. We express our sincere gratitude and appreciation to the OurDIU team, student contributors, and class representatives (CRs) for voluntarily archiving these academic resources.

### 2. Unofficial & Educational Purpose (Fair Use)
- **Non-Affiliation**: This is an **independent, unofficial open-source project**. It is not officially affiliated with, authorized, maintained, sponsored, or endorsed by Daffodil International University (DIU) or OurDIU.
- **Academic & Non-Commercial Use**: This project is developed strictly for **academic study, research, accessibility, and educational assistance** under fair use principles. No content is commercialized or sold.
- **Intellectual Property & Copyrights**: All copyrights to examination question papers, course curriculum, and institutional trademarks belong to Daffodil International University and the respective course instructors. This tool acts solely as an intelligent search, accessibility, and indexing interface.

### 3. Content Removal & Takedown Policy
If you are an authorized representative of Daffodil International University, a faculty member, or a copyright owner and wish to request the removal or restriction of any specific question paper or indexed link, please open an Issue on this repository or contact the maintainer. We respect intellectual property rights and will honor legitimate removal requests promptly.

---

## 📜 License

This project is open-source and licensed under the [MIT License](LICENSE).
