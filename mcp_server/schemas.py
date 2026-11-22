"""Pydantic schemas and argument models for MCP tools."""

from typing import List, Union, Optional
from pydantic import BaseModel, Field


class ListCoursesArgs(BaseModel):
    department: str = Field(
        description="Department name or short code (e.g. 'CSE', 'EEE', 'BBA', or 'Computer Science and Engineering')."
    )


class ListSemestersArgs(BaseModel):
    department: str = Field(
        description="Department name or short code (e.g. 'CSE')."
    )
    course: str = Field(
        description="Course name or code (e.g. 'CSE 221', 'Operating Systems', 'Algorithms')."
    )


class ListExamTypesArgs(BaseModel):
    department: str = Field(
        description="Department name or short code (e.g. 'CSE')."
    )
    course: str = Field(
        description="Course name or code (e.g. 'Operating Systems')."
    )


class SearchQuestionsArgs(BaseModel):
    department: str = Field(
        description="Department name or short code (e.g. 'CSE')."
    )
    course: str = Field(
        description="Course name or code (e.g. 'Operating Systems' or 'CSE 221')."
    )
    semesters: Union[str, List[str]] = Field(
        default="all",
        description="Semesters to search. Default is 'all'. Can be a single semester like 'Fall 2024' or a list like ['Fall 2024', 'Spring 2025']."
    )
    exam_types: Union[str, List[str]] = Field(
        default="all",
        description="Exam types to filter. Options: 'midterm', 'final', 'quiz', or 'all'. Can be a single string or list like ['midterm', 'final']."
    )


class CollectQuestionsArgs(BaseModel):
    department: str = Field(
        description="Department name or short code (e.g. 'CSE'). Prompt the user if not specified."
    )
    course: str = Field(
        description="Course name or code (e.g. 'Operating Systems'). Prompt the user if not specified."
    )
    semesters: Union[str, List[str]] = Field(
        default="all",
        description="Semesters to collect. Default is 'all'. Can be a single semester (e.g. 'Fall 2024') or a list (e.g. ['Fall 2024', 'Spring 2025']) or 'all' for every semester."
    )
    exam_types: Union[str, List[str]] = Field(
        default="all",
        description="Exam types to collect: 'midterm', 'final', 'quiz', or 'all'. Multiple selections allowed (e.g. ['midterm', 'final'])."
    )
    force_refresh: bool = Field(
        default=False,
        description="Set to true to re-download files even if already cached locally."
    )


class ListCollectedFilesArgs(BaseModel):
    bundle_id: Optional[str] = Field(
        default=None,
        description="Optional bundle/collection ID to filter collected files. If omitted, returns recent collected files."
    )


class GetPdfFileArgs(BaseModel):
    file_id: str = Field(
        description="Unique identifier of the PDF file (e.g. 'pdf_1949_2967') returned from collect_questions or list_collected_files."
    )


class GetSummaryArgs(BaseModel):
    collection_id: str = Field(
        description="Unique collection / bundle ID returned from collect_questions."
    )
