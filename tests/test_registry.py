"""
Tests for the core registry functionality.
"""

import json
import pytest
import os
from cuebit.registry import PromptRegistry

def test_registry_initialization(temp_db_path):
    """Test registry initialization with custom DB path."""
    registry = PromptRegistry(db_url=temp_db_path)
    assert registry.db_url == temp_db_path
    
    # Check if DB was created
    db_path = temp_db_path.replace("sqlite:///", "")
    assert os.path.exists(db_path)

def test_env_variable_db_path(monkeypatch):
    """Test registry respects environment variable for DB path."""
    test_path = "sqlite:///test_env_db.db"
    monkeypatch.setenv("CUEBIT_DB_PATH", test_path)
    
    registry = PromptRegistry()
    assert registry.db_url == test_path

def test_register_prompt(empty_registry):
    """Test registering a new prompt."""
    prompt = empty_registry.register_prompt(
        task="test-task",
        template="Test template with {variable}",
        meta={"test": "data"},
        tags=["test", "example"],
        project="test-project",
        updated_by="test-user"
    )
    
    # Verify prompt was created
    assert prompt.prompt_id is not None
    assert prompt.task == "test-task"
    assert prompt.template == "Test template with {variable}"
    assert prompt.meta == {"test": "data"}
    assert json.loads(prompt.tags) == ["test", "example"]
    assert prompt.project == "test-project"
    assert prompt.updated_by == "test-user"
    assert prompt.version == 1
    
    # Verify template variables were extracted
    assert prompt.template_variables == ["variable"]

def test_get_prompt(sample_registry):
    """Test retrieving a prompt."""
    # Get all prompts
    prompts, _ = sample_registry.list_prompts()
    
    # Get a specific prompt
    prompt_id = prompts[0].prompt_id
    prompt = sample_registry.get_prompt(prompt_id)
    
    # Verify retrieval
    assert prompt is not None
    assert prompt.prompt_id == prompt_id

def test_get_prompt_by_alias(sample_registry):
    """Test retrieving a prompt by alias."""
    prompt = sample_registry.get_prompt_by_alias("test-summarizer")
    
    # Verify retrieval
    assert prompt is not None
    assert prompt.task == "summarization"

def test_update_prompt(sample_registry):
    """Test updating a prompt."""
    # Get the first prompt
    prompts, _ = sample_registry.list_prompts()
    prompt_id = prompts[0].prompt_id
    
    # Update it
    updated = sample_registry.update_prompt(
        prompt_id=prompt_id,
        new_template="Updated template: {input}",
        meta={"model": "gpt-4", "temperature": 0.8},
        updated_by="updater",
        tags=["updated", "test"]
    )
    
    # Verify update
    assert updated is not None
    assert updated.prompt_id != prompt_id  # New ID for new version
    assert updated.template == "Updated template: {input}"
    assert updated.meta["temperature"] == 0.8
    assert updated.updated_by == "updater"
    assert updated.version > prompts[0].version
    assert updated.parent_id == prompt_id  # Links to parent
    
    # Verify lineage
    lineage = sample_registry.get_prompt_lineage(prompt_id)
    assert lineage["descendants"][0].prompt_id == updated.prompt_id

def test_add_alias(sample_registry):
    """Test adding an alias to a prompt."""
    # Get a prompt without an alias
    prompts, _ = sample_registry.list_prompts()
    prompt_id = None
    
    for p in prompts:
        if p.alias is None:
            prompt_id = p.prompt_id
            break
    
    if prompt_id is None:
        # Create a new prompt if all have aliases
        prompt = sample_registry.register_prompt(
            task="alias-test",
            template="Template for alias test",
            meta={}
        )
        prompt_id = prompt.prompt_id
    
    # Add alias
    alias_name = "test-alias-new"
    aliased = sample_registry.add_alias(prompt_id, alias_name)
    
    # Verify alias
    assert aliased is not None
    assert aliased.alias == alias_name
    
    # Verify retrieval by alias
    retrieved = sample_registry.get_prompt_by_alias(alias_name)
    assert retrieved is not None
    assert retrieved.prompt_id == prompt_id

def test_list_projects(sample_registry):
    """Test listing projects."""
    projects = sample_registry.list_projects()
    
    # Verify projects
    assert "test-project" in projects
    assert "translation-project" in projects

def test_list_prompts_by_project(sample_registry):
    """Test listing prompts by project."""
    prompts = sample_registry.list_prompts_by_project("test-project")
    
    # Verify prompts
    assert len(prompts) > 0
    assert all(p.project == "test-project" for p in prompts)
    
    # Check versions
    assert any(p.version == 1 for p in prompts)
    assert any(p.version == 2 for p in prompts)

def test_get_version_history(sample_registry):
    """Test getting version history."""
    history = sample_registry.get_version_history("test-project", "summarization")
    
    # Verify history
    assert len(history) == 2
    assert any(p.version == 1 for p in history)
    assert any(p.version == 2 for p in history)

def test_compare_versions(sample_registry):
    """Test comparing prompt versions."""
    # Get two versions of the same prompt
    history = sample_registry.get_version_history("test-project", "summarization")
    assert len(history) >= 2
    
    # Sort by version
    sorted_history = sorted(history, key=lambda p: p.version)
    v1 = sorted_history[0]
    v2 = sorted_history[1]
    
    # Compare
    comparison = sample_registry.compare_versions(v1.prompt_id, v2.prompt_id)
    
    # Verify comparison
    assert "template_diff" in comparison
    assert "meta_changes" in comparison
    assert "tags_changes" in comparison
    assert "variables_changes" in comparison
    assert "prompts" in comparison
    
    # Verify template diff
    assert len(comparison["template_diff"]) > 0
    
    # Verify tag changes
    assert "concise" in comparison["tags_changes"]["added"]

def test_export_import(sample_registry):
    """Test exporting and importing prompts with detailed debugging."""
    import os
    import tempfile
    import json
    from sqlalchemy import create_engine
    from cuebit.registry import PromptRegistry, Base
    
    print("\n----- DEBUG: Starting test_export_import -----")
    
    # First ensure sample_registry has data by adding a new prompt
    prompt = sample_registry.register_prompt(
        task="export-import-test",
        template="Test template for export/import",
        meta={"model": "gpt-4", "temperature": 0.7},
        tags=["test", "export", "import"],
        project="export-import-project",
        updated_by="test-user"
    )
    
    print(f"DEBUG: Created new prompt with ID: {prompt.prompt_id}")
    
    # Verify prompt was created successfully
    verify_prompt = sample_registry.get_prompt(prompt.prompt_id)
    print(f"DEBUG: Verification - get_prompt returned: {verify_prompt.prompt_id if verify_prompt else 'None'}")
    
    # Add an alias to test alias import/export
    alias_result = sample_registry.add_alias(prompt.prompt_id, "export-import-alias")
    print(f"DEBUG: Add alias result: {alias_result.prompt_id if alias_result else 'Failed'}")
    
    # Check if alias was set correctly
    alias_prompt = sample_registry.get_prompt_by_alias("export-import-alias")
    print(f"DEBUG: Alias verification - get_prompt_by_alias returned: {alias_prompt.prompt_id if alias_prompt else 'None'}")
    
    # Export prompts
    exported = sample_registry.export_prompts(format="json")
    print(f"DEBUG: Exported data length: {len(exported) if exported else 0} characters")
    
    # Examine the exported data
    try:
        parsed_export = json.loads(exported)
        print(f"DEBUG: Parsed export has {len(parsed_export)} items")
        
        # Check if our prompt is in the export
        found = False
        for idx, p in enumerate(parsed_export):
            if p.get("prompt_id") == prompt.prompt_id:
                found = True
                print(f"DEBUG: Found our prompt at index {idx}")
                print(f"DEBUG: Export object: {json.dumps(p, indent=2)}")
                break
        
        if not found:
            print(f"DEBUG: WARNING - Our prompt was NOT found in the export!")
            # Print first object as sample
            if parsed_export:
                print(f"DEBUG: Sample export object: {json.dumps(parsed_export[0], indent=2)}")
    except Exception as e:
        print(f"DEBUG: Error parsing export data: {str(e)}")
        print(f"DEBUG: Export data sample: {exported[:200]}...")
    
    # Create a completely new database for testing import
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "import_test.db")
    db_url = f"sqlite:///{db_path}"
    print(f"DEBUG: Created new DB at: {db_url}")
    
    # Create and initialize the database
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    print("DEBUG: Created database schema")
    
    # Create a new registry instance
    new_registry = PromptRegistry(db_url=db_url)
    print(f"DEBUG: Created new registry with DB URL: {new_registry.db_url}")
    
    # Save the export to a file for inspection
    debug_file = os.path.join(temp_dir, "debug_export.json")
    with open(debug_file, 'w') as f:
        f.write(exported)
    print(f"DEBUG: Saved export to: {debug_file}")
    
    # Directly import from the file to avoid any issues with string passing
    with open(debug_file, 'r') as f:
        file_content = f.read()
    print(f"DEBUG: Read {len(file_content)} characters from file")
    
    # Import the previously exported data
    results = new_registry.import_prompts(file_content, format="json")
    print(f"DEBUG: Import results: {results}")
    
    # Check error details if any
    if results.get("errors", 0) > 0:
        print(f"DEBUG: Import error details: {results.get('error_details', [])}")
    
    # Check if any prompts were imported
    prompts, count = new_registry.list_prompts()
    print(f"DEBUG: After import, found {count} prompts in new registry")
    
    # Try to get the prompt by alias
    imported_alias = new_registry.get_prompt_by_alias("export-import-alias")
    print(f"DEBUG: get_prompt_by_alias result: {imported_alias.prompt_id if imported_alias else 'None'}")
    
    print("----- DEBUG: Finishing test_export_import -----\n")
    
    # Now make the actual assertions
    assert results["imported"] >= 1, f"Expected at least 1 prompt to be imported, got {results['imported']}"
    
    # Check if our test prompt was imported by looking for its alias
    assert imported_alias is not None, "Failed to import the test prompt with alias"
    
    # Cleanup the temporary database
    os.unlink(db_path)
    os.unlink(debug_file)
    os.rmdir(temp_dir)
    
def test_soft_delete_restore(sample_registry):
    """Test soft deleting and restoring prompts."""
    # Get a prompt
    prompts, _ = sample_registry.list_prompts()
    prompt_id = prompts[0].prompt_id
    
    # Soft delete it
    success = sample_registry.soft_delete_prompt(prompt_id)
    assert success is True
    
    # Verify it's not listed by default
    prompts, _ = sample_registry.list_prompts()
    assert not any(p.prompt_id == prompt_id for p in prompts)
    
    # Verify it can be retrieved with include_deleted
    deleted_prompt = sample_registry.get_prompt(prompt_id, include_deleted=True)
    assert deleted_prompt is not None
    assert deleted_prompt.is_deleted is True
    
    # Restore it
    success = sample_registry.restore_prompt(prompt_id)
    assert success is True
    
    # Verify it's listed again
    prompts, _ = sample_registry.list_prompts()
    assert any(p.prompt_id == prompt_id for p in prompts)

def test_validate_template(empty_registry):
    """Test template validation."""
    # Valid template
    valid = empty_registry.validate_template("Test template with {variable}")
    assert valid["is_valid"] is True
    assert "variable" in valid["variables"]
    
    # Invalid template (unclosed brackets)
    invalid = empty_registry.validate_template("Test template with {variable")
    assert invalid["is_valid"] is False
    assert len(invalid["warnings"]) > 0
    
    # No variables
    no_vars = empty_registry.validate_template("Test template with no variables")
    assert no_vars["is_valid"] is True
    assert len(no_vars["variables"]) == 0
    assert "No variables found" in no_vars["warnings"][0]

def test_examples(sample_registry):
    """Test working with examples."""
    # Get a prompt to work with
    prompts, _ = sample_registry.list_prompts()
    prompt_id = prompts[0].prompt_id
    
    # Get existing examples
    examples = sample_registry.get_examples(prompt_id)
    
    # Add a new example
    new_example = sample_registry.add_example(
        prompt_id,
        input_text="Example input text",
        output_text="Example output text",
        description="Test example"
    )
    
    assert new_example is not None
    assert new_example.input_text == "Example input text"
    
    # Verify example was added
    updated_examples = sample_registry.get_examples(prompt_id)
    assert len(updated_examples) == len(examples) + 1
    
    # Verify the new example is in the list
    assert any(ex["input"] == "Example input text" for ex in updated_examples)

def test_render_prompt(sample_registry):
    """Test rendering a prompt with variables."""
    # Get the summarization prompt
    prompt = sample_registry.get_prompt_by_alias("test-summarizer")
    
    # Render it
    rendered = sample_registry.render_prompt(
        prompt.prompt_id,
        {"input": "This is a test input"}
    )
    
    # Verify rendering
    assert rendered is not None
    assert "This is a test input" in rendered