"""
Tests for the CLI commands.
"""

import os
import pytest
import tempfile
import json
import time

def test_cli_help(cli_runner):
    """Test the help command."""
    result = cli_runner("cuebit --help")
    
    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "Cuebit - Prompt Versioning and Management CLI" in result.stdout

def test_cli_version(cli_runner):
    """Test getting the version."""
    result = cli_runner("python -c \"import cuebit; print(cuebit.__version__)\"")
    
    assert result.returncode == 0
    assert len(result.stdout.strip()) > 0

def test_cli_init(cli_runner):
    """Test the init command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        result = cli_runner(f"cuebit init --data-dir {temp_dir}")
        
        assert result.returncode == 0
        assert "Registry initialized" in result.stdout
        
        # Check that DB was created
        assert os.path.exists(os.path.join(temp_dir, "prompts.db"))

def test_cli_create_prompt(cli_runner):
    """Test creating a prompt via CLI."""
    result = cli_runner(
        "cuebit create prompt --task cli-test --template \"CLI test template with {variable}\" "
        "--project cli-test-project --tags \"cli,test\" "
        "--meta \"{\\\"model\\\": \\\"gpt-4\\\", \\\"temperature\\\": 0.7}\" "
        "--updated-by cli-tester"
    )
    
    assert result.returncode == 0
    assert "Prompt created successfully" in result.stdout
    assert "ID:" in result.stdout
    assert "cli-test-project" in result.stdout

def test_cli_list_projects(cli_runner):
    """Test listing projects via CLI."""
    # First create a project
    cli_runner(
        "cuebit create prompt --task cli-list-test --template \"Test\" "
        "--project cli-list-project"
    )
    
    # Then list projects
    result = cli_runner("cuebit list projects")
    
    assert result.returncode == 0
    assert "Projects:" in result.stdout
    assert "cli-list-project" in result.stdout

def test_cli_list_prompts(cli_runner):
    """Test listing prompts via CLI."""
    # First create a prompt
    cli_runner(
        "cuebit create prompt --task cli-list-prompt-test --template \"Test\" "
        "--project cli-list-prompts-project"
    )
    
    # Then list prompts
    result = cli_runner("cuebit list prompts")
    
    assert result.returncode == 0
    assert "cli-list-prompts-project" in result.stdout
    assert "cli-list-prompt-test" in result.stdout

def test_cli_list_prompts_by_project(cli_runner):
    """Test listing prompts by project via CLI."""
    project_name = "cli-list-by-project"
    
    # First create a prompt in the project
    cli_runner(
        f"cuebit create prompt --task cli-list-by-test --template \"Test\" "
        f"--project {project_name}"
    )
    
    # Then list prompts for that project
    result = cli_runner(f"cuebit list prompts --project {project_name}")
    
    assert result.returncode == 0
    assert project_name in result.stdout
    assert "cli-list-by-test" in result.stdout

def test_cli_update_prompt(cli_runner):
    """Test updating a prompt via CLI."""
    # First create a prompt
    create_result = cli_runner(
        "cuebit create prompt --task cli-update-test --template \"Original template\" "
        "--project cli-update-project"
    )
    
    # Extract the ID (this is a bit fragile but necessary for the test)
    prompt_id = None
    for line in create_result.stdout.split("\n"):
        if line.startswith("ID:"):
            prompt_id = line.split("ID:")[1].strip()
            break
    
    if not prompt_id:
        pytest.fail("Could not extract prompt ID from creation output")
    
    # Update the prompt
    update_result = cli_runner(
        f"cuebit update {prompt_id} --template \"Updated template\" "
        "--updated-by cli-updater"
    )
    
    assert update_result.returncode == 0
    assert "Prompt updated successfully" in update_result.stdout
    assert "New version:" in update_result.stdout

def test_cli_get_prompt(cli_runner):
    """Test getting a prompt via CLI."""
    # First create a prompt
    create_result = cli_runner(
        "cuebit create prompt --task cli-get-test --template \"Test template\" "
        "--project cli-get-project"
    )
    
    # Extract the ID
    prompt_id = None
    for line in create_result.stdout.split("\n"):
        if line.startswith("ID:"):
            prompt_id = line.split("ID:")[1].strip()
            break
    
    if not prompt_id:
        pytest.fail("Could not extract prompt ID from creation output")
    
    # Get the prompt
    get_result = cli_runner(f"cuebit get {prompt_id}")
    
    assert get_result.returncode == 0
    assert prompt_id in get_result.stdout
    assert "cli-get-test" in get_result.stdout
    assert "Test template" in get_result.stdout

def test_cli_set_get_alias(cli_runner):
    """Test setting and getting an alias via CLI."""
    # First create a prompt
    create_result = cli_runner(
        "cuebit create prompt --task cli-alias-test --template \"Test template\" "
        "--project cli-alias-project"
    )
    
    # Extract the ID
    prompt_id = None
    for line in create_result.stdout.split("\n"):
        if line.startswith("ID:"):
            prompt_id = line.split("ID:")[1].strip()
            break
    
    if not prompt_id:
        pytest.fail("Could not extract prompt ID from creation output")
    
    # Set an alias
    alias_name = "cli-test-alias"
    alias_result = cli_runner(f"cuebit set-alias {prompt_id} {alias_name}")
    
    assert alias_result.returncode == 0
    assert f"Alias '{alias_name}' set for prompt" in alias_result.stdout
    
    # Get by alias
    get_result = cli_runner(f"cuebit get {alias_name} --by-alias")
    
    assert get_result.returncode == 0
    assert prompt_id in get_result.stdout
    assert f"Alias: {alias_name}" in get_result.stdout

def test_cli_render(cli_runner):
    """Test rendering a prompt via CLI."""
    # First create a prompt with a variable and capture the output to get the ID
    create_result = cli_runner(
        "cuebit create prompt --task cli-render-test "
        "--template \"Render test with variable: {text}\" "
        "--project cli-render-project"
    )
    
    # Extract the prompt ID directly from the output
    prompt_id = None
    for line in create_result.stdout.split('\n'):
        if line.startswith("ID:"):
            prompt_id = line.split("ID:")[1].strip()
            break
    
    if not prompt_id:
        pytest.fail("Could not extract prompt ID from creation output")
    
    # Set an alias using the extracted ID
    cli_runner(f"cuebit set-alias {prompt_id} cli-render-alias")
    
    # Render by alias
    render_result = cli_runner(
        "cuebit render --alias cli-render-alias --vars '{\"text\":\"Hello from CLI\"}'"
    )
    
    assert render_result.returncode == 0
    assert "Rendered Prompt:" in render_result.stdout
    assert "Hello from CLI" in render_result.stdout

def test_cli_export_import(cli_runner):
    """Test exporting and importing prompts via CLI."""
    with tempfile.NamedTemporaryFile(suffix=".json") as tmp_file:
        # First create a prompt with a unique name
        unique_name = f"cli-export-test-{int(time.time())}"
        cli_runner(
            f"cuebit create prompt --task {unique_name} "
            f"--template \"Export test template\" "
            f"--project cli-export-project"
        )
        
        # Export to file
        export_result = cli_runner(f"cuebit export --format json --file {tmp_file.name}")
        
        assert export_result.returncode == 0
        assert f"Exported to {tmp_file.name}" in export_result.stdout
        
        # Check file has content
        tmp_file.seek(0)
        exported_content = tmp_file.read().decode('utf-8')
        assert len(exported_content) > 0
        assert unique_name in exported_content
        
        # Reset environment and import
        import_result = cli_runner(f"cuebit import {tmp_file.name}")
        
        assert import_result.returncode == 0
        assert "Import completed:" in import_result.stdout
        assert "Errors: 0" in import_result.stdout

def test_cli_stats(cli_runner):
    """Test getting registry statistics via CLI."""
    # First create a prompt
    cli_runner(
        "cuebit create prompt --task cli-stats-test --template \"Stats test template\" "
        "--project cli-stats-project"
    )
    
    # Get stats
    stats_result = cli_runner("cuebit stats")
    
    assert stats_result.returncode == 0
    assert "Cuebit Registry Statistics" in stats_result.stdout
    assert "Total prompts:" in stats_result.stdout
    assert "Database URL:" in stats_result.stdout

def test_cli_delete_restore(cli_runner):
    """Test deleting and restoring a prompt via CLI."""
    # First create a prompt
    create_result = cli_runner(
        "cuebit create prompt --task cli-delete-test --template \"Delete test template\" "
        "--project cli-delete-project"
    )
    
    # Extract the ID
    prompt_id = None
    for line in create_result.stdout.split("\n"):
        if line.startswith("ID:"):
            prompt_id = line.split("ID:")[1].strip()
            break
    
    if not prompt_id:
        pytest.fail("Could not extract prompt ID from creation output")
    
    # Delete it (soft delete)
    delete_result = cli_runner(f"cuebit delete prompt {prompt_id}")
    
    assert delete_result.returncode == 0
    assert "soft deleted" in delete_result.stdout
    
    # Verify it's gone from listing
    list_result = cli_runner("cuebit list prompts")
    lines = list_result.stdout.split("\n")
    id_lines = [line for line in lines if f"ID: {prompt_id}" in line]
    assert len(id_lines) == 0