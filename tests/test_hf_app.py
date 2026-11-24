"""Tests for Hugging Face Spaces Gradio + FastAPI entrypoint."""

import pytest
from app import app, search_questions_ui, preview_page_ui


def test_gradio_app_structure():
    """Verify that app is a FastAPI instance with Gradio mounted."""
    assert app is not None
    # Check that FastAPI routes still include Swagger, OpenAPI, and health
    routes = [route.path for route in app.routes if hasattr(route, "path")]
    assert "/docs" in routes
    assert "/openapi.json" in routes
    assert "/health" in routes
    assert "/api/departments" in routes
    assert "/api/search" in routes
    assert "/api/collect" in routes
    assert "/api/files/{file_id}/download" in routes
    # MCP SSE app must be mounted exactly once (regression: duplicate /mcp mount).
    assert routes.count("/mcp") == 1


@pytest.mark.asyncio
async def test_search_ui_empty_result():
    """Verify search UI handles non-existent courses gracefully."""
    result_md, file_id = await search_questions_ui(
        department="CSE",
        course="NonExistentCourseXYZ123",
        semester="all",
        exam_type="all",
    )
    assert "No question papers found" in result_md or "Error" in result_md
    assert file_id is None
