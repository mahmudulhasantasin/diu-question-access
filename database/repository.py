"""SQLite repository for storing and caching DIU question records and PDFs."""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from config import DB_PATH
from database.models import (
    Department, Course, Semester, ExamType, ExamRecord, PDFMetadata, CollectionRecord
)


class DatabaseRepository:
    """Manages SQLite storage for question records, PDF metadata, and collections."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    short_name TEXT NOT NULL,
                    published_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    department_id INTEGER NOT NULL,
                    published_count INTEGER DEFAULT 0,
                    aliases TEXT DEFAULT '[]',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (department_id) REFERENCES departments(id)
                );

                CREATE TABLE IF NOT EXISTS semesters (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS exam_types (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    normalized TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pdf_files (
                    file_id TEXT PRIMARY KEY,
                    question_id INTEGER NOT NULL,
                    submission_id INTEGER NOT NULL,
                    department_short TEXT NOT NULL,
                    department_name TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    course_code TEXT NOT NULL,
                    semester TEXT NOT NULL,
                    exam_type TEXT NOT NULL,
                    section TEXT,
                    batch TEXT,
                    source_url TEXT NOT NULL,
                    pdf_url TEXT NOT NULL UNIQUE,
                    local_path TEXT NOT NULL,
                    download_status TEXT NOT NULL,
                    download_timestamp TEXT,
                    file_size INTEGER DEFAULT 0,
                    sha256 TEXT,
                    error_message TEXT,
                    question_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_pdf_sha256 ON pdf_files(sha256);
                CREATE INDEX IF NOT EXISTS idx_pdf_url ON pdf_files(pdf_url);
                CREATE INDEX IF NOT EXISTS idx_pdf_question_id ON pdf_files(question_id);

                CREATE TABLE IF NOT EXISTS collections (
                    collection_id TEXT PRIMARY KEY,
                    department TEXT NOT NULL,
                    course TEXT NOT NULL,
                    semesters TEXT NOT NULL,
                    exam_types TEXT NOT NULL,
                    total_exams INTEGER DEFAULT 0,
                    total_pdfs INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS collection_files (
                    collection_id TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    PRIMARY KEY (collection_id, file_id),
                    FOREIGN KEY (collection_id) REFERENCES collections(collection_id),
                    FOREIGN KEY (file_id) REFERENCES pdf_files(file_id)
                );
            """)

            # Auto-migration: ensure question_text column exists in existing pdf_files tables
            cursor = conn.execute("PRAGMA table_info(pdf_files)")
            cols = [c[1] for c in cursor.fetchall()]
            if "question_text" not in cols and len(cols) > 0:
                conn.execute("ALTER TABLE pdf_files ADD COLUMN question_text TEXT")

    # ---------------- Department Operations ----------------
    def upsert_departments(self, departments: List[Department]) -> None:
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT INTO departments (id, name, short_name, published_count, updated_at)
                VALUES (:id, :name, :short_name, :published_count, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    short_name=excluded.short_name,
                    published_count=excluded.published_count,
                    updated_at=CURRENT_TIMESTAMP
            """, [d.to_dict() for d in departments])

    def get_all_departments(self) -> List[Department]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT id, name, short_name, published_count FROM departments ORDER BY name").fetchall()
            return [Department(**dict(row)) for row in rows]

    def find_department(self, identifier: str) -> Optional[Department]:
        ident = identifier.strip().lower()
        with self._get_connection() as conn:
            # Match by id, short_name, or name
            row = conn.execute("""
                SELECT id, name, short_name, published_count FROM departments
                WHERE CAST(id AS TEXT) = ? OR LOWER(short_name) = ? OR LOWER(name) = ?
                LIMIT 1
            """, (ident, ident, ident)).fetchone()
            if row:
                return Department(**dict(row))
            # Substring match on name
            row = conn.execute("""
                SELECT id, name, short_name, published_count FROM departments
                WHERE LOWER(name) LIKE ?
                LIMIT 1
            """, (f"%{ident}%",)).fetchone()
            return Department(**dict(row)) if row else None

    # ---------------- Course Operations ----------------
    def upsert_courses(self, courses: List[Course]) -> None:
        with self._get_connection() as conn:
            for c in courses:
                conn.execute("""
                    INSERT INTO courses (id, name, department_id, published_count, aliases, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        department_id=excluded.department_id,
                        published_count=excluded.published_count,
                        aliases=excluded.aliases,
                        updated_at=CURRENT_TIMESTAMP
                """, (c.id, c.name, c.department_id, c.published_count, json.dumps(c.aliases)))

    def get_courses_by_department(self, department_id: int) -> List[Course]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, name, department_id, published_count, aliases FROM courses
                WHERE department_id = ?
                ORDER BY name
            """, (department_id,)).fetchall()
            courses = []
            for r in rows:
                d = dict(r)
                d["aliases"] = json.loads(d["aliases"]) if d.get("aliases") else []
                courses.append(Course(**d))
            return courses

    def find_course(self, department_id: int, query: str) -> Optional[Course]:
        q = query.strip().lower()
        courses = self.get_courses_by_department(department_id)
        # 1. Exact ID match
        for c in courses:
            if str(c.id) == q:
                return c
        # 2. Exact name match
        for c in courses:
            if c.name.lower() == q:
                return c
        # 3. Exact alias match
        for c in courses:
            for a in c.aliases:
                if a.lower() == q:
                    return c
        # 4. Partial substring match in name or aliases
        for c in courses:
            if q in c.name.lower():
                return c
            for a in c.aliases:
                if q in a.lower():
                    return c
        return None

    # ---------------- Semester Operations ----------------
    def upsert_semesters(self, semesters: List[Semester]) -> None:
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT INTO semesters (id, name, updated_at)
                VALUES (:id, :name, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    updated_at=CURRENT_TIMESTAMP
            """, [s.to_dict() for s in semesters])

    def get_all_semesters(self) -> List[Semester]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT id, name FROM semesters ORDER BY id DESC").fetchall()
            return [Semester(**dict(r)) for r in rows]

    # ---------------- Exam Type Operations ----------------
    def upsert_exam_types(self, exam_types: List[ExamType]) -> None:
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT INTO exam_types (id, name, normalized)
                VALUES (:id, :name, :normalized)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    normalized=excluded.normalized
            """, [e.to_dict() for e in exam_types])

    def get_all_exam_types(self) -> List[ExamType]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT id, name, normalized FROM exam_types").fetchall()
            return [ExamType(**dict(r)) for r in rows]

    # ---------------- PDF File & Caching Operations ----------------
    def upsert_pdf_file(self, meta: PDFMetadata) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO pdf_files (
                    file_id, question_id, submission_id, department_short, department_name,
                    course_name, course_code, semester, exam_type, section, batch,
                    source_url, pdf_url, local_path, download_status, download_timestamp,
                    file_size, sha256, error_message, question_text
                ) VALUES (
                    :file_id, :question_id, :submission_id, :department_short, :department_name,
                    :course_name, :course_code, :semester, :exam_type, :section, :batch,
                    :source_url, :pdf_url, :local_path, :download_status, :download_timestamp,
                    :file_size, :sha256, :error_message, :question_text
                )
                ON CONFLICT(file_id) DO UPDATE SET
                    download_status=excluded.download_status,
                    download_timestamp=excluded.download_timestamp,
                    local_path=excluded.local_path,
                    file_size=excluded.file_size,
                    sha256=excluded.sha256,
                    error_message=excluded.error_message,
                    question_text=excluded.question_text
            """, meta.to_dict())

    def get_pdf_by_id(self, file_id: str) -> Optional[PDFMetadata]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM pdf_files WHERE file_id = ?", (file_id,)).fetchone()
            if row:
                d = dict(row)
                d.pop("created_at", None)
                return PDFMetadata(**d)
            return None

    def get_pdf_by_url(self, pdf_url: str) -> Optional[PDFMetadata]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM pdf_files WHERE pdf_url = ?", (pdf_url,)).fetchone()
            if row:
                d = dict(row)
                d.pop("created_at", None)
                return PDFMetadata(**d)
            return None

    def get_pdf_by_sha256(self, sha256: str) -> Optional[PDFMetadata]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM pdf_files WHERE sha256 = ? AND download_status = 'downloaded' LIMIT 1",
                (sha256,)
            ).fetchone()
            if row:
                d = dict(row)
                d.pop("created_at", None)
                return PDFMetadata(**d)
            return None

    # ---------------- Collection & Bundle Operations ----------------
    def record_collection(
        self,
        collection_id: str,
        department: str,
        course: str,
        semesters: List[str],
        exam_types: List[str],
        total_exams: int,
        total_pdfs: int,
        file_ids: List[str],
    ) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO collections (
                    collection_id, department, course, semesters, exam_types,
                    total_exams, total_pdfs, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                collection_id,
                department,
                course,
                json.dumps(semesters),
                json.dumps(exam_types),
                total_exams,
                total_pdfs,
            ))
            conn.executemany("""
                INSERT OR IGNORE INTO collection_files (collection_id, file_id)
                VALUES (?, ?)
            """, [(collection_id, fid) for fid in file_ids])

    def get_collection(self, collection_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM collections WHERE collection_id = ?", (collection_id,)).fetchone()
            if not row:
                return None
            res = dict(row)
            res["semesters"] = json.loads(res["semesters"])
            res["exam_types"] = json.loads(res["exam_types"])
            return res

    def get_files_for_collection(self, collection_id: str) -> List[PDFMetadata]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT p.* FROM pdf_files p
                JOIN collection_files cf ON p.file_id = cf.file_id
                WHERE cf.collection_id = ?
                ORDER BY p.semester DESC, p.exam_type ASC, p.question_id ASC
            """, (collection_id,)).fetchall()
            files = []
            for r in rows:
                d = dict(r)
                d.pop("created_at", None)
                files.append(PDFMetadata(**d))
            return files
