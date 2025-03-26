"""
Tests for the FastAPI endpoints.
"""

import json
import pytest
from fastapi.testclient import TestClient

def test_health_endpoint(api_client):
    """Test the health check endpoint."""
    response = api_client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "database_url" in response.json()

def test_root_endpoint(api_client):
    """Test the root endpoint."""
    response = api_client.get("/")
    
    assert response.status_code == 200
    assert "message" in response.json()
    assert "docs" in response.json()
    assert "version" in response.json()
    assert "database_url" in response.json()

def test_list_projects(api_client):
    """Test listing projects."""
    response = api_client.get("/api/v1/projects")
    
    assert response.status_code == 200
    assert "test-project" in response.json()

def test_list_prompts(api_client):
    """Test listing prompts."""
    response = api_client.get("/api/v1/prompts")
    
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "page_size" in response.json()
    assert "pages" in response.json()
    assert len(response.json()["items"]) > 0

def test_list_prompts_filtering(api_client):
    """Test listing prompts with filtering."""
    # Create a test prompt with unique content
    create_response = api_client.post(
        "/api/v1/prompts",
        json={
            "task": "filtered-task",
            "template": "Unique template for filtering tests",
            "meta": {"test": "filter"},
            "tags": ["filter-test"],
            "project": "filtering-project"
        }
    )
    assert create_response.status_code == 200
    
    # Test search filtering
    search_response = api_client.get("/api/v1/prompts?search=Unique+template")
    assert search_response.status_code == 200
    assert search_response.json()["total"] >= 1
    assert any("Unique template" in p["template"] for p in search_response.json()["items"])
    
    # Test tag filtering
    tag_response = api_client.get("/api/v1/prompts?tags=filter-test")
    assert tag_response.status_code == 200
    assert tag_response.json()["total"] >= 1
    
    # Test project filtering
    project_prompts_response = api_client.get("/api/v1/projects/filtering-project/prompts")
    assert project_prompts_response.status_code == 200
    assert len(project_prompts_response.json()) >= 1

def test_create_prompt(api_client):
    """Test creating a new prompt."""
    response = api_client.post(
        "/api/v1/prompts",
        json={
            "task": "api-test-task",
            "template": "API test template with {variable}",
            "meta": {"test": "api-test"},
            "tags": ["api", "test"],
            "project": "api-test-project",
            "updated_by": "api-tester",
            "examples": [
                {
                    "input": "API test input",
                    "output": "API test output",
                    "description": "API test example"
                }
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["task"] == "api-test-task"
    assert data["template"] == "API test template with {variable}"
    assert data["meta"] == {"test": "api-test"}
    assert "prompt_id" in data

def test_get_prompt(api_client):
    """Test getting a prompt by ID."""
    # First, list prompts to get an ID
    list_response = api_client.get("/api/v1/prompts")
    assert list_response.status_code == 200
    prompts = list_response.json()["items"]
    
    if not prompts:
        pytest.skip("No prompts available for testing get prompt endpoint")
    
    prompt_id = prompts[0]["prompt_id"]
    
    # Now get the prompt
    response = api_client.get(f"/api/v1/prompts/{prompt_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["prompt_id"] == prompt_id

def test_get_prompt_by_alias(api_client):
    """Test getting a prompt by alias."""
    response = api_client.get("/api/v1/prompts/alias/test-alias")
    
    assert response.status_code == 200
    data = response.json()
    assert "prompt_id" in data
    assert data["task"] == "test-task"

def test_update_prompt(api_client):
    """Test updating a prompt."""
    # First, list prompts to get an ID
    list_response = api_client.get("/api/v1/prompts")
    assert list_response.status_code == 200
    prompts = list_response.json()["items"]
    
    if not prompts:
        pytest.skip("No prompts available for testing update prompt endpoint")
    
    prompt_id = prompts[0]["prompt_id"]
    
    # Now update the prompt
    response = api_client.put(
        f"/api/v1/prompts/{prompt_id}",
        json={
            "new_template": "Updated by API test: {variable}",
            "meta": {"updated": "by-api"},
            "updated_by": "api-updater",
            "tags": ["updated", "api"]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["template"] == "Updated by API test: {variable}"
    assert data["meta"]["updated"] == "by-api"
    assert data["updated_by"] == "api-updater"
    assert data["version"] > prompts[0]["version"]

def test_set_alias(api_client):
    """Test setting an alias."""
    # First, list prompts to get an ID
    list_response = api_client.get("/api/v1/prompts")
    assert list_response.status_code == 200
    prompts = list_response.json()["items"]
    
    if not prompts:
        pytest.skip("No prompts available for testing set alias endpoint")
    
    prompt_id = prompts[0]["prompt_id"]
    
    # Set an alias
    response = api_client.post(
        f"/api/v1/prompts/{prompt_id}/alias",
        json={
            "alias": "api-test-alias",
            "overwrite": True
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["alias"] == "api-test-alias"
    
    # Verify alias works
    alias_response = api_client.get("/api/v1/prompts/alias/api-test-alias")
    assert alias_response.status_code == 200
    assert alias_response.json()["prompt_id"] == prompt_id

def test_render_prompt(api_client):
    """Test rendering a prompt."""
    # First, list prompts to get an ID
    list_response = api_client.get("/api/v1/prompts")
    assert list_response.status_code == 200
    prompts = list_response.json()["items"]
    
    if not prompts:
        pytest.skip("No prompts available for testing render prompt endpoint")
    
    prompt_id = None
    for p in prompts:
        if p["template_variables"] and len(p["template_variables"]) > 0:
            prompt_id = p["prompt_id"]
            variable = p["template_variables"][0]
            break
    
    if prompt_id is None:
        pytest.skip("No prompts with variables available for testing render endpoint")
    
    # Render the prompt
    response = api_client.post(
        "/api/v1/prompts/render",
        json={
            "prompt_id": prompt_id,
            "variables": {variable: "API test variable value"}
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "rendered" in data
    assert "API test variable value" in data["rendered"]

def test_validate_template(api_client):
    """Test validating a template."""
    response = api_client.post(
        "/api/v1/prompts/validate",
        json="Test template with {variable1} and {variable2}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert "variable1" in data["variables"]
    assert "variable2" in data["variables"]

def test_prompt_history_lineage(api_client):
    """Test prompt history and lineage endpoints."""
    # Create a prompt
    create_response = api_client.post(
        "/api/v1/prompts",
        json={
            "task": "history-test",
            "template": "Template for history test",
            "project": "history-project"
        }
    )
    assert create_response.status_code == 200
    prompt_id = create_response.json()["prompt_id"]
    
    # Update it to create history
    update_response = api_client.put(
        f"/api/v1/prompts/{prompt_id}",
        json={
            "new_template": "Updated template for history test",
            "updated_by": "history-tester"
        }
    )
    assert update_response.status_code == 200
    
    # Get history
    history_response = api_client.get(f"/api/v1/prompts/{prompt_id}/history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 2
    
    # Get lineage
    lineage_response = api_client.get(f"/api/v1/prompts/{prompt_id}/lineage")
    assert lineage_response.status_code == 200
    lineage = lineage_response.json()
    assert lineage["current"]["prompt_id"] == prompt_id
    assert len(lineage["descendants"]) == 1

def test_compare_prompts(api_client):
    """Test comparing prompts endpoint."""
    # Create a prompt
    create_response = api_client.post(
        "/api/v1/prompts",
        json={
            "task": "compare-test",
            "template": "Template for compare test",
            "tags": ["compare", "v1"],
            "project": "compare-project"
        }
    )
    assert create_response.status_code == 200
    prompt_id_1 = create_response.json()["prompt_id"]
    
    # Update it to create a second version
    update_response = api_client.put(
        f"/api/v1/prompts/{prompt_id_1}",
        json={
            "new_template": "Updated template for compare test",
            "tags": ["compare", "v2"],
            "updated_by": "compare-tester"
        }
    )
    assert update_response.status_code == 200
    prompt_id_2 = update_response.json()["prompt_id"]
    
    # Compare the versions
    compare_response = api_client.post(
        "/api/v1/prompts/compare",
        json={
            "prompt_id_1": prompt_id_1,
            "prompt_id_2": prompt_id_2
        }
    )
    
    assert compare_response.status_code == 200
    comparison = compare_response.json()
    assert "template_diff" in comparison
    assert "meta_changes" in comparison
    assert "tags_changes" in comparison
    assert "variables_changes" in comparison
    assert "v2" in comparison["tags_changes"]["added"]

def test_export_import(api_client):
    """Test export and import endpoints."""
    # Export all prompts
    export_response = api_client.get("/api/v1/export")
    assert export_response.status_code == 200
    exported_data = export_response.text
    
    # Delete all prompts by creating a new client
    # (This is simulated by importing into the existing client)
    
    # Import the data
    import_response = api_client.post(
        "/api/v1/import",
        json={
            "data": exported_data,
            "format": "json",
            "skip_existing": True
        }
    )
    
    assert import_response.status_code == 200
    import_result = import_response.json()
    assert import_result["imported"] >= 0
    assert import_result["skipped"] >= 0
    assert import_result["errors"] == 0

def test_delete_restore_prompt(api_client):
    """Test deleting and restoring a prompt."""
    # Create a prompt
    create_response = api_client.post(
        "/api/v1/prompts",
        json={
            "task": "delete-test",
            "template": "Template for delete test",
            "project": "delete-project"
        }
    )
    assert create_response.status_code == 200
    prompt_id = create_response.json()["prompt_id"]
    
    # Delete it (soft delete)
    delete_response = api_client.delete(f"/api/v1/prompts/{prompt_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True
    
    # Verify it's deleted
    get_response = api_client.get(f"/api/v1/prompts/{prompt_id}")
    assert get_response.status_code == 404
    
    # Restore it
    restore_response = api_client.post(f"/api/v1/prompts/{prompt_id}/restore")
    assert restore_response.status_code == 200
    assert restore_response.json()["success"] is True
    
    # Verify it's restored
    get_response_after = api_client.get(f"/api/v1/prompts/{prompt_id}")
    assert get_response_after.status_code == 200
    assert get_response_after.json()["prompt_id"] == prompt_id