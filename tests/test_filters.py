"""Unit tests for semester and exam type filtering and normalization."""

import pytest
from scraper.semesters import normalize_semester_str, semester_matches
from scraper.exams import normalize_exam_type, exam_type_matches


def test_normalize_semester_str():
    assert normalize_semester_str("Fall 2024") == "fall 24"
    assert normalize_semester_str("Spring 2025") == "spring 25"
    assert normalize_semester_str("Summer 2023") == "summer 23"
    assert normalize_semester_str("Fall 24") == "fall 24"
    assert normalize_semester_str("fall24") == "fall 24"
    assert normalize_semester_str("Spring-2022") == "spring 22"
    assert normalize_semester_str("Fall '24") == "fall 24"


def test_semester_all_filter():
    assert semester_matches("Fall 24", "all") is True
    assert semester_matches("Spring 25", "ALL") is True
    assert semester_matches("Summer 22", "*") is True
    assert semester_matches("Fall 23", "all semesters") is True
    assert semester_matches("Fall 24", ["all"]) is True


def test_semester_single_selection():
    assert semester_matches("Fall 24", "Fall 2024") is True
    assert semester_matches("Fall 24", "fall 24") is True
    assert semester_matches("Fall 24", "Fall 24") is True
    assert semester_matches("Fall 24", "Spring 2024") is False
    assert semester_matches("Spring 25", "Spring 2025") is True
    assert semester_matches("Spring 25", "Fall 25") is False


def test_semester_multiple_selection():
    selected = ["Fall 2024", "Spring 2025", "Summer 2025"]
    assert semester_matches("Fall 24", selected) is True
    assert semester_matches("Spring 25", selected) is True
    assert semester_matches("Summer 25", selected) is True
    assert semester_matches("Fall 23", selected) is False
    assert semester_matches("Spring 24", selected) is False


def test_normalize_exam_type():
    # Midterm variants
    assert normalize_exam_type("mid") == "midterm"
    assert normalize_exam_type("midterm") == "midterm"
    assert normalize_exam_type("Midterm Examination") == "midterm"
    assert normalize_exam_type("mid term") == "midterm"
    assert normalize_exam_type("MID-TERM") == "midterm"

    # Final variants
    assert normalize_exam_type("final") == "final"
    assert normalize_exam_type("Final Examination") == "final"
    assert normalize_exam_type("term final") == "final"
    assert normalize_exam_type("FINAL") == "final"

    # Quiz variants
    assert normalize_exam_type("quiz") == "quiz"
    assert normalize_exam_type("Class Test") == "quiz"
    assert normalize_exam_type("CT") == "quiz"
    assert normalize_exam_type("class-test") == "quiz"

    # Unrecognized / custom exam types preserved
    assert normalize_exam_type("Lab Assessment") == "lab assessment"
    assert normalize_exam_type("Special Assignment") == "special assignment"


def test_exam_type_all_filter():
    assert exam_type_matches("Midterm", "all") is True
    assert exam_type_matches("Final", "*") is True
    assert exam_type_matches("Quiz", "all exam types") is True
    assert exam_type_matches("Midterm", ["all"]) is True


def test_exam_type_single_selection():
    assert exam_type_matches("Midterm", "midterm") is True
    assert exam_type_matches("Midterm Examination", "midterm") is True
    assert exam_type_matches("Final", "final") is True
    assert exam_type_matches("Class Test", "quiz") is True
    assert exam_type_matches("Final", "midterm") is False
    assert exam_type_matches("Quiz", "final") is False


def test_exam_type_multiple_selection():
    selected = ["midterm", "final"]
    assert exam_type_matches("Midterm", selected) is True
    assert exam_type_matches("Final Examination", selected) is True
    assert exam_type_matches("Quiz", selected) is False
    assert exam_type_matches("Class Test", selected) is False
