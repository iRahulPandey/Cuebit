"""
Update to conftest.py to improve test database handling.
"""

import os
import tempfile
import pytest
import shutil
import uuid
from pathlib import Path
from sqlalchemy import create_engine

from cuebit.registry import PromptRegistry, Base

@pytest.fixture(scope="function")
def temp_db_path():
    """Provide a temporary database path for testing."""
    # Create temporary directory with unique name
    temp_dir = tempfile.mkdtemp(prefix=f"cuebit_test_{uuid.uuid4()}_")
    db_path = os.path.join(temp_dir, "test_prompts.db")
    db_url = f"sqlite:///{db_path}"
    
    # Yield the URL
    yield db_url
    
    # Clean up after test
    shutil.rmtree(temp_dir)

@pytest.fixture(scope="function")
def empty_registry(temp_db_path):
    """Provide an empty registry with a clean database."""
    # Make sure directory exists
    path = temp_db_path.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Create engine and tables
    engine = create_engine(temp_db_path)
    Base.metadata.create_all(engine)
    
    # Create registry with this path
    registry = PromptRegistry(db_url=temp_db_path)
    
    # Return the registry for the test to use
    return registry

@pytest.fixture(scope="function")
def sample_registry(empty_registry):
    """Provide a registry with sample data."""
    # Create a sample project with multiple prompt versions
    prompt1 = empty_registry.register_prompt(
        task="summarization",
        template="Summarize this text: {input}",
        meta={"model": "gpt-4", "temperature": 0.7},
        tags=["test", "summarization"],
        project="test-project",
        updated_by="test-user"
    )
    
    # Add an alias
    empty_registry.add_alias(prompt1.prompt_id, "test-summarizer")
    
    # Create a second version
    prompt2 = empty_registry.update_prompt(
        prompt_id=prompt1.prompt_id,
        new_template="Provide a concise summary: {input}",
        meta={"model": "gpt-4", "temperature": 0.5},
        updated_by="test-user",
        tags=["test", "summarization", "concise"]
    )
    
    # Create a prompt in a different project
    prompt3 = empty_registry.register_prompt(
        task="translation",
        template="Translate from {source_lang} to {target_lang}: {text}",
        meta={"model": "gpt-4", "temperature": 0.3},
        tags=["test", "translation"],
        project="translation-project",
        updated_by="test-user"
    )
    
    # Add an example to prompt1
    empty_registry.add_example(
        prompt1.prompt_id,
        input_text="The quick brown fox jumps over the lazy dog.",
        output_text="A fox jumps over a dog.",
        description="Simple test example"
    )
    
    return empty_registry

@pytest.fixture(scope="function")
def api_client(temp_db_path):
    """Provide a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    
    # Dynamically import and patch the server
    import cuebit.server as server_module
    from cuebit.server import app
    
    # Create a new registry
    test_registry = PromptRegistry(db_url=temp_db_path)
    
    # Save the original registry to restore later
    original_registry = server_module.registry
    
    # Replace the registry in the server
    server_module.registry = test_registry
    
    # Create a test client
    client = TestClient(app)
    
    # Adding a sample prompt for testing
    prompt = test_registry.register_prompt(
        task="test-task",
        template="Test template with {variable}",
        meta={"test": "data"},
        project="test-project"
    )
    test_registry.add_alias(prompt.prompt_id, "test-alias")
    
    yield client
    
    # Restore the original registry
    server_module.registry = original_registry

@pytest.fixture(scope="function")
def cli_runner(temp_db_path):
    """Provide a CLI command runner with isolated environment."""
    import subprocess
    import os
    
    def run_cli_command(command, env=None):
        """Run a CLI command and return its output."""
        # Create custom environment with test database
        test_env = os.environ.copy()
        
        # Use the temp database
        test_env["CUEBIT_DB_PATH"] = temp_db_path
        if env:
            test_env.update(env)
        
        # Run the command
        process = subprocess.run(
            command,
            env=test_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True
        )
        
        return process
    
    return run_cli_command