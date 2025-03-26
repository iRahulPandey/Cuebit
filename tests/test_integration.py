"""
Integration tests for end-to-end workflows.
"""

import os
import time
import json
import pytest
import tempfile
from fastapi.testclient import TestClient

from cuebit.registry import PromptRegistry
from cuebit.server import app

@pytest.fixture
def integrated_env():
    """Create an integrated environment with registry, API, and CLI access."""
    import tempfile
    import shutil
    import os
    
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "integration_test.db")
    db_url = f"sqlite:///{db_path}"
    
    # Set environment variable for DB path
    os.environ["CUEBIT_DB_PATH"] = db_url
    
    # Create registry and API client
    registry = PromptRegistry(db_url=db_url)
    
    # Patch the server registry
    import cuebit.server
    original_registry = cuebit.server.registry
    cuebit.server.registry = registry
    
    # Create API client using the same DB
    client = TestClient(app)
    
    # Function to run CLI commands
    def run_cli(command):
        import subprocess
        full_command = f"CUEBIT_DB_PATH={db_url} {command}"
        process = subprocess.run(
            full_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        return process
    
    # Return all components
    yield {
        "registry": registry,
        "api": client,
        "cli": run_cli,
        "db_url": db_url
    }
    
    # Restore the original registry
    cuebit.server.registry = original_registry
    
    # Clean up
    shutil.rmtree(temp_dir)

def test_create_update_retrieve_workflow(integrated_env):
    """Test a full workflow: create -> update -> retrieve via registry, API, and CLI."""
    registry = integrated_env["registry"]
    api = integrated_env["api"]
    cli = integrated_env["cli"]
    
    # 1. Create a prompt via Registry
    prompt = registry.register_prompt(
        task="integration-test",
        template="Integration test template with {variable}",
        meta={"model": "gpt-4", "temperature": 0.7},
        tags=["integration", "test"],
        project="integration-project",
        updated_by="integration-tester"
    )
    
    prompt_id = prompt.prompt_id
    assert prompt_id is not None
    
    # 2. Update the prompt via API
    update_response = api.put(
        f"/api/v1/prompts/{prompt_id}",
        json={
            "new_template": "Updated by API: {variable}",
            "meta": {"updated_by": "api"},
            "tags": ["integration", "test", "api"],
            "updated_by": "api-updater"
        }
    )
    assert update_response.status_code == 200
    updated_prompt_id = update_response.json()["prompt_id"]
    
    # 3. Set an alias via CLI
    alias_result = cli(f"cuebit set-alias {updated_prompt_id} integration-alias")
    assert alias_result.returncode == 0
    assert "integration-alias" in alias_result.stdout
    
    # 4. Retrieve via Registry by alias
    retrieved = registry.get_prompt_by_alias("integration-alias")
    assert retrieved is not None
    assert retrieved.prompt_id == updated_prompt_id
    assert "Updated by API" in retrieved.template
    
    # 5. Retrieve via API by ID
    api_response = api.get(f"/api/v1/prompts/{updated_prompt_id}")
    assert api_response.status_code == 200
    assert api_response.json()["prompt_id"] == updated_prompt_id
    
    # 6. Verify CLI can see it
    cli_result = cli("cuebit list prompts")
    assert cli_result.returncode == 0
    assert "integration-project" in cli_result.stdout
    assert "integration-test" in cli_result.stdout

def test_export_import_workflow(integrated_env):
    """Test exporting and importing workflows across registry, API, and CLI."""
    registry = integrated_env["registry"]
    api = integrated_env["api"]
    cli = integrated_env["cli"]
    
    # Create a unique prompt for testing
    unique_name = f"export-import-{int(time.time())}"
    prompt = registry.register_prompt(
        task=unique_name,
        template="Export/import test template",
        meta={"test": "export-import"},
        project="export-import-project"
    )
    
    # 1. Export via Registry
    exported_json = registry.export_prompts(format="json")
    assert unique_name in exported_json
    
    # 2. Export via API
    api_export = api.get("/api/v1/export?format=json")
    assert api_export.status_code == 200
    assert unique_name in api_export.text
    
    # Create a temporary file for CLI export/import
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # 3. Export via CLI to file
        cli_export = cli(f"cuebit export --format json --file {tmp_path}")
        assert cli_export.returncode == 0
        
        # Verify file contains the prompt
        with open(tmp_path, 'r') as f:
            file_content = f.read()
            assert unique_name in file_content
        
        # 4. Reset DB and import via Registry
        with tempfile.TemporaryDirectory() as new_temp_dir:
            new_db_path = os.path.join(new_temp_dir, "new_db.db")
            new_db_url = f"sqlite:///{new_db_path}"
            
            new_registry = PromptRegistry(db_url=new_db_url)
            import_results = new_registry.import_prompts(exported_json, format="json")
            
            assert import_results["imported"] > 0
            assert import_results["errors"] == 0
            
            # Verify import worked
            imported_prompts, _ = new_registry.list_prompts()
            assert any(p.task == unique_name for p in imported_prompts)
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def test_version_history_workflow(integrated_env):
    """Test version history and rollback workflows."""
    registry = integrated_env["registry"]
    api = integrated_env["api"]
    
    # 1. Create a prompt
    prompt = registry.register_prompt(
        task="history-test",
        template="History test template v1",
        meta={"version": 1},
        project="history-project"
    )
    prompt_id = prompt.prompt_id
    
    # 2. Update it multiple times
    prompt_v2 = registry.update_prompt(
        prompt_id=prompt_id,
        new_template="History test template v2",
        meta={"version": 2}
    )
    
    prompt_v3 = registry.update_prompt(
        prompt_id=prompt_v2.prompt_id,
        new_template="History test template v3",
        meta={"version": 3}
    )
    
    # 3. Get history via Registry
    history = registry.get_version_history("history-project", "history-test")
    assert len(history) == 3
    assert any(p.version == 1 for p in history)
    assert any(p.version == 2 for p in history)
    assert any(p.version == 3 for p in history)
    
    # 4. Get history via API
    api_history = api.get(f"/api/v1/prompts/{prompt_v3.prompt_id}/history")
    assert api_history.status_code == 200
    
    # 5. Compare versions via API
    compare_response = api.post(
        "/api/v1/prompts/compare",
        json={
            "prompt_id_1": prompt_id,
            "prompt_id_2": prompt_v3.prompt_id
        }
    )
    assert compare_response.status_code == 200
    
    comparison = compare_response.json()
    assert "template_diff" in comparison
    
    # 6. Rollback to v1 via API
    rollback_response = api.post(f"/api/v1/prompts/{prompt_id}/rollback")
    assert rollback_response.status_code == 200
    
    # Verify rollback created v4 with v1's content
    rollback_prompt = rollback_response.json()
    assert rollback_prompt["version"] == 4
    assert rollback_prompt["template"] == "History test template v1"
    assert "rollback" in rollback_prompt["meta"]

def test_search_and_filter_workflow(integrated_env):
    """Test searching and filtering workflows."""
    registry = integrated_env["registry"]
    api = integrated_env["api"]
    
    # Create prompts with different properties for filtering
    registry.register_prompt(
        task="filter-task-1",
        template="Filterable template with apple",
        meta={"fruit": "apple"},
        tags=["filter", "fruit", "apple"],
        project="filter-project"
    )
    
    registry.register_prompt(
        task="filter-task-2",
        template="Filterable template with banana",
        meta={"fruit": "banana"},
        tags=["filter", "fruit", "banana"],
        project="filter-project"
    )
    
    registry.register_prompt(
        task="filter-task-3",
        template="Filterable template with cherry",
        meta={"fruit": "cherry"},
        tags=["filter", "fruit", "cherry"],
        project="other-project"
    )
    
    # 1. Search by text via Registry
    apple_results, apple_count = registry.search_prompts("apple")
    assert apple_count >= 1
    assert any("apple" in p.template for p in apple_results)
    
    # 2. Filter by project via Registry
    project_prompts = registry.list_prompts_by_project("filter-project")
    assert len(project_prompts) == 2
    assert all(p.project == "filter-project" for p in project_prompts)
    
    # 3. Search by text via API
    api_search = api.post(
        "/api/v1/prompts/search",
        json={
            "query": "banana",
            "page": 1,
            "page_size": 10
        }
    )
    assert api_search.status_code == 200
    assert api_search.json()["total"] >= 1
    
    # 4. Filter by tags via API
    tag_search = api.post(
        "/api/v1/prompts/search",
        json={
            "query": "filter",
            "tags": ["cherry"],
            "page": 1,
            "page_size": 10
        }
    )
    assert tag_search.status_code == 200
    assert tag_search.json()["total"] >= 1
    
    # 5. Filter by project via API
    project_filter = api.get("/api/v1/projects/other-project/prompts")
    assert project_filter.status_code == 200
    assert len(project_filter.json()) >= 1
    assert all(p["project"] == "other-project" for p in project_filter.json())

def test_aliasing_workflow(integrated_env):
    """Test alias management workflows."""
    registry = integrated_env["registry"]
    api = integrated_env["api"]
    cli = integrated_env["cli"]
    
    # 1. Create a prompt (add required meta parameter)
    prompt = registry.register_prompt(
        task="alias-test",
        template="Alias test template v1",
        meta={},  # Empty dict but satisfies the requirement
        project="alias-project"
    )
    prompt_id = prompt.prompt_id
    
    # 2. Set alias via Registry
    registry.add_alias(prompt_id, "alias-test-1")
    
    # 3. Verify alias works
    by_alias = registry.get_prompt_by_alias("alias-test-1")
    assert by_alias is not None
    assert by_alias.prompt_id == prompt_id
    
    # 4. Update prompt
    prompt_v2 = registry.update_prompt(
        prompt_id=prompt_id,
        new_template="Alias test template v2",
        meta={}  # Empty dict but satisfies the requirement
    )
    
    # 5. Set new alias via API
    api_alias = api.post(
        f"/api/v1/prompts/{prompt_v2.prompt_id}/alias",
        json={
            "alias": "alias-test-2",
            "overwrite": False
        }
    )
    assert api_alias.status_code == 200
    
    # 6. Verify both aliases work
    api_get_1 = api.get("/api/v1/prompts/alias/alias-test-1")
    assert api_get_1.status_code == 200
    assert api_get_1.json()["prompt_id"] == prompt_id
    
    api_get_2 = api.get("/api/v1/prompts/alias/alias-test-2")
    assert api_get_2.status_code == 200
    assert api_get_2.json()["prompt_id"] == prompt_v2.prompt_id
    
    # 7. Update alias via CLI
    cli_result = cli(f"cuebit set-alias {prompt_id} alias-test-3")
    assert cli_result.returncode == 0
    
    # 8. Verify CLI alias works
    cli_check = cli("cuebit get alias-test-3 --by-alias")
    assert cli_check.returncode == 0
    assert prompt_id in cli_check.stdout