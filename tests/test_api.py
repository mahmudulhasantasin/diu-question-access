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


def test_mcp_jsonrpc_streamable_http(client):
    # 1. Test initialize (used by Gemini & Streamable HTTP clients)
    init_res = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"}
    })
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert init_data["id"] == 1
    assert "tools" in init_data["result"]["capabilities"]

    # 2. Test tools/list (used by Gemini & Streamable HTTP clients)
    tools_res = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    })
    assert tools_res.status_code == 200
    tools_data = tools_res.json()
    assert "tools" in tools_data["result"]
    assert len(tools_data["result"]["tools"]) == 10
    tools_by_name = {t["name"]: t for t in tools_data["result"]["tools"]}
    schema = tools_by_name["search_questions"]["inputSchema"]
    assert schema.get("type") == "object"
    assert "department" in schema.get("properties", {})
    assert "course" in schema.get("properties", {})
    # Every tool must expose a non-empty parameter schema.
    for name, tool in tools_by_name.items():
        assert tool["inputSchema"].get("properties"), f"Tool '{name}' is missing its input schema."

    # 3. Test tools/call (used by Gemini & Streamable HTTP clients)
    call_res = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "list_departments",
            "arguments": {"force_refresh": False}
        }
    })
    assert call_res.status_code == 200
    call_data = call_res.json()
    assert call_data["result"]["isError"] is False
    assert len(call_data["result"]["content"]) > 0


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
