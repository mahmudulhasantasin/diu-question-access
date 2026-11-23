"""Unit tests for production FastAPI REST & OpenAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from api import create_app

@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint(client):
    # Test GET /
    res_get = client.get("/")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["status"] == "online"
    assert "docs_url" in data
    assert "openapi_url" in data

    # Test HEAD / (Render health check probe)
    res_head = client.head("/")
    assert res_head.status_code == 200


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "version" in data
    assert "DIU Question" in data["service"]


def test_openapi_schema(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema
    assert "/api/departments" in schema["paths"]
    assert "/api/courses" in schema["paths"]
    assert "/api/collect" in schema["paths"]
    assert "/health" in schema["paths"]


def test_docs_swagger_ui(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower() or "html" in response.text.lower()


def test_api_departments(client):
    response = client.get("/api/departments")
    assert response.status_code == 200
    depts = response.json()
    assert isinstance(depts, list)
    assert len(depts) > 0
    assert any(d.get("short_name") == "CSE" for d in depts)


def test_api_courses(client):
    response = client.get("/api/courses?department=CSE")
    assert response.status_code == 200
    courses = response.json()
    assert isinstance(courses, list)
    assert len(courses) > 0
    assert any("operating" in c.get("name", "").lower() for c in courses)


def test_api_invalid_department(client):
    response = client.get("/api/courses?department=NON_EXISTENT_DEPT_XYZ")
    assert response.status_code == 404
