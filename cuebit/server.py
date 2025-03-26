"""
FastAPI server for Cuebit prompt management.

This module provides a REST API for accessing and managing
Cuebit prompts, with endpoints for listing, creating, updating,
and comparing prompt versions.
"""

from fastapi import FastAPI, HTTPException, Body, Query, Path, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
import json
import os
import copy

from cuebit.registry import PromptRegistry, PromptORM, ExampleORM

# Helper functions for serialization
def orm_to_dict(orm_obj):
    """
    Convert SQLAlchemy ORM object to a dictionary for serialization.
    """
    if not orm_obj:
        return None
        
    data = {}
    for column in orm_obj.__table__.columns:
        value = getattr(orm_obj, column.name)
        
        # Handle special types
        if isinstance(value, datetime):
            value = value.isoformat()
            
        data[column.name] = value
        
    return data

def convert_orm_list(orm_list):
    """Convert a list of ORM objects to a list of dictionaries."""
    return [orm_to_dict(item) for item in orm_list]

# Constants
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# Initialize the app
app = FastAPI(
    title="Cuebit Prompt API",
    version="1.0",
    openapi_url=f"{API_PREFIX}/openapi.json",
    docs_url=f"{API_PREFIX}/docs",
)

# Enable CORS for external frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize registry using the improved initialization
# It will respect CUEBIT_DB_PATH environment variable
# or use the standard data directory
registry = PromptRegistry()

# --- Pydantic Models ---

class PaginatedResponse(BaseModel):
    """Response model for paginated results."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    pages: int

class ExampleIn(BaseModel):
    """Input model for prompt examples."""
    input: str
    output: str
    description: Optional[str] = None

class PromptCreate(BaseModel):
    """Input model for creating a new prompt."""
    task: str
    template: str
    tags: Optional[List[str]] = []
    meta: Dict[str, Any] = {}
    project: Optional[str] = None
    updated_by: Optional[str] = None
    examples: Optional[List[ExampleIn]] = None

    class Config:
        schema_extra = {
            "example": {
                "task": "summarization",
                "template": "Summarize the following text: {input}",
                "tags": ["prod", "nlp"],
                "meta": {"model": "gpt-4", "temperature": 0.7},
                "project": "content-generator",
                "updated_by": "alice",
                "examples": [
                    {
                        "input": "The quick brown fox jumps over the lazy dog.",
                        "output": "A fox jumps over a dog.",
                        "description": "Basic summarization"
                    }
                ]
            }
        }

class PromptUpdate(BaseModel):
    """Input model for updating a prompt."""
    new_template: str
    meta: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    updated_by: Optional[str] = None
    examples: Optional[List[ExampleIn]] = None

class PromptOut(BaseModel):
    """Output model for prompt data."""
    prompt_id: str
    task: str
    template: str
    version: int
    alias: Optional[str] = None
    project: Optional[str] = None
    tags: str
    meta: Dict[str, Any]
    parent_id: Optional[str] = None
    template_variables: List[str] = []
    created_at: Union[datetime, str]
    updated_at: Union[datetime, str]
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True  # This replaces orm_mode in Pydantic v2

    @classmethod
    def from_orm(cls, obj):
        """Create a model instance from an ORM object."""
        if obj is None:
            return None
        # Convert ORM object to dict
        data = orm_to_dict(obj)
        # Return instance
        return cls(**data)

class AliasCreate(BaseModel):
    """Input model for creating an alias."""
    alias: str
    overwrite: bool = True

class PromptRenderRequest(BaseModel):
    """Input model for rendering a prompt with variables."""
    prompt_id: str
    variables: Dict[str, str]

class PromptCompareRequest(BaseModel):
    """Input model for comparing two prompts."""
    prompt_id_1: str
    prompt_id_2: str

class SearchQuery(BaseModel):
    """Input model for prompt search."""
    query: str
    project: Optional[str] = None
    tags: Optional[List[str]] = []
    page: int = 1
    page_size: int = 20

class BulkTagRequest(BaseModel):
    """Input model for bulk tagging prompts."""
    prompt_ids: List[str]
    tags: List[str]
    operation: str = "add"  # "add", "remove", "set"

class ImportRequest(BaseModel):
    """Input model for importing prompts."""
    data: str
    format: str = "json"
    skip_existing: bool = True

class ExampleOut(BaseModel):
    """Output model for prompt examples."""
    id: int
    input: str
    output: str
    description: Optional[str]
    created_at: Union[datetime, str]

# --- Project Endpoints ---

@app.get(f"{API_PREFIX}/projects", response_model=List[str], 
         summary="List all projects", 
         description="Returns a list of all projects in the registry.")
def list_projects():
    """Return a list of all projects in the registry."""
    return registry.list_projects()

@app.get(
    f"{API_PREFIX}/projects/{{project}}/prompts", 
    response_model=List[Dict[str, Any]],
    summary="List prompts in a project",
    description="Returns all prompts belonging to a specific project."
)
def get_project_prompts(
    project: str = Path(..., description="Project name to filter"),
    include_deleted: bool = Query(False, description="Whether to include soft-deleted prompts")
):
    """Return all prompts belonging to a specific project."""
    prompts = registry.list_prompts_by_project(project, include_deleted=include_deleted)
    return [orm_to_dict(p) for p in prompts]

@app.delete(
    f"{API_PREFIX}/projects/{{project}}",
    summary="Delete a project",
    description="Delete all prompts in a project (soft delete by default)."
)
def delete_project(
    project: str = Path(..., description="Project name to delete"),
    use_soft_delete: bool = Query(True, description="Whether to use soft delete (True) or hard delete (False)")
):
    """Delete all prompts in a project."""
    deleted = registry.delete_project(project, use_soft_delete=use_soft_delete)
    return {"deleted": deleted, "project": project}

@app.delete(
    f"{API_PREFIX}/projects/{{project}}/tasks/{{task}}",
    summary="Delete task in project",
    description="Delete all prompts for a specific task in a project."
)
def delete_project_task(
    project: str = Path(..., description="Project name"),
    task: str = Path(..., description="Task name"),
    use_soft_delete: bool = Query(True, description="Whether to use soft delete (True) or hard delete (False)")
):
    """Delete all prompts for a task in a project."""
    deleted = registry.delete_prompts_by_project_task(
        project, task, use_soft_delete=use_soft_delete
    )
    return {"deleted": deleted, "project": project, "task": task}

# --- Prompt Endpoints ---

@app.get(
    f"{API_PREFIX}/prompts", 
    response_model=PaginatedResponse,
    summary="List prompts",
    description="List all prompts with pagination and filtering options."
)
def list_prompts(
    page: int = Query(1, description="Page number (starts at 1)"),
    page_size: int = Query(20, description="Items per page"),
    include_deleted: bool = Query(False, description="Include soft-deleted prompts"),
    search: Optional[str] = Query(None, description="Search term"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by")
):
    """List all prompts with pagination and filtering."""
    # Parse tag filter if provided
    tag_filter = tags.split(",") if tags else None
    
    prompts, total = registry.list_prompts(
        include_deleted=include_deleted,
        search_term=search,
        tag_filter=tag_filter,
        page=page,
        page_size=page_size
    )
    
    pages = (total + page_size - 1) // page_size  # Ceiling division
    
    # Convert ORM objects to dictionaries
    prompt_dicts = [orm_to_dict(p) for p in prompts]
    
    return {
        "items": prompt_dicts,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
    }

@app.post(
    f"{API_PREFIX}/prompts", 
    response_model=Dict[str, Any],
    summary="Create a prompt",
    description="Register a new prompt template with metadata."
)
def create_prompt(
    prompt: PromptCreate
):
    """Register a new prompt template."""
    # Convert examples if provided
    examples_list = None
    if prompt.examples:
        examples_list = [
            {
                "input": ex.input,
                "output": ex.output,
                "description": ex.description
            }
            for ex in prompt.examples
        ]
        
    result = registry.register_prompt(
        task=prompt.task,
        template=prompt.template,
        meta=prompt.meta,
        tags=prompt.tags,
        project=prompt.project,
        updated_by=prompt.updated_by,
        examples=examples_list
    )
    
    # Return as dictionary to avoid serialization issues
    return orm_to_dict(result)

@app.get(
    f"{API_PREFIX}/prompts/{{prompt_id}}", 
    response_model=Dict[str, Any],
    summary="Get a prompt",
    description="Retrieve a specific prompt by its ID."
)
def get_prompt(
    prompt_id: str = Path(..., description="The UUID of the prompt"),
    include_deleted: bool = Query(False, description="Include soft-deleted prompts")
):
    """Get a specific prompt by ID."""
    prompt = registry.get_prompt(prompt_id, include_deleted=include_deleted)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return orm_to_dict(prompt)

@app.put(
    f"{API_PREFIX}/prompts/{{prompt_id}}", 
    response_model=Dict[str, Any],
    summary="Update a prompt",
    description="Update a prompt, creating a new version."
)
def update_prompt(
    prompt_id: str = Path(..., description="Prompt ID to update"),
    update: PromptUpdate = Body(..., description="Update data")
):
    """Update a prompt (creates a new version)."""
    # Convert examples if provided
    examples_list = None
    if update.examples:
        examples_list = [
            {
                "input": ex.input,
                "output": ex.output,
                "description": ex.description
            }
            for ex in update.examples
        ]
        
    prompt = registry.update_prompt(
        prompt_id, 
        update.new_template, 
        update.meta, 
        update.updated_by,
        update.tags,
        examples_list
    )
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return orm_to_dict(prompt)

@app.post(
    f"{API_PREFIX}/prompts/{{prompt_id}}/alias", 
    response_model=Dict[str, Any],
    summary="Set alias for prompt",
    description="Set an alias for a specific prompt version."
)
def alias_prompt(
    prompt_id: str = Path(..., description="Prompt ID to alias"),
    alias_data: AliasCreate = Body(..., description="Alias data")
):
    """Set an alias for a prompt."""
    prompt = registry.add_alias(
        prompt_id, 
        alias_data.alias, 
        overwrite=alias_data.overwrite
    )
    
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return orm_to_dict(prompt)

@app.get(
    f"{API_PREFIX}/prompts/alias/{{alias}}", 
    response_model=Dict[str, Any],
    summary="Get prompt by alias",
    description="Retrieve a prompt using its alias."
)
def get_prompt_by_alias(
    alias: str = Path(..., description="Alias to look up")
):
    """Get a prompt by its alias."""
    prompt = registry.get_prompt_by_alias(alias)
    if not prompt:
        raise HTTPException(status_code=404, detail="Alias not found")
    return orm_to_dict(prompt)

@app.delete(
    f"{API_PREFIX}/prompts/{{prompt_id}}",
    summary="Delete a prompt",
    description="Delete a prompt (soft delete by default)."
)
def delete_prompt(
    prompt_id: str = Path(..., description="Prompt ID to delete"),
    hard_delete: bool = Query(False, description="Use hard delete instead of soft delete"),
    deleted_by: Optional[str] = Query(None, description="User performing the deletion")
):
    """Delete a prompt."""
    if hard_delete:
        success = registry.delete_prompt_by_id(prompt_id)
    else:
        success = registry.soft_delete_prompt(prompt_id, deleted_by=deleted_by)
        
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"success": True, "prompt_id": prompt_id, "hard_delete": hard_delete}

@app.post(
    f"{API_PREFIX}/prompts/{{prompt_id}}/restore",
    summary="Restore a prompt",
    description="Restore a soft-deleted prompt."
)
def restore_prompt(
    prompt_id: str = Path(..., description="Prompt ID to restore")
):
    """Restore a soft-deleted prompt."""
    success = registry.restore_prompt(prompt_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found or not deleted")
    return {"success": True, "prompt_id": prompt_id}

# --- Advanced Prompt Management ---

@app.post(
    f"{API_PREFIX}/prompts/render",
    summary="Render a prompt",
    description="Render a prompt template with variable values."
)
def render_prompt(
    request: PromptRenderRequest = Body(..., description="Render request")
):
    """Render a prompt template with provided variables."""
    rendered = registry.render_prompt(request.prompt_id, request.variables)
    if rendered is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"rendered": rendered, "prompt_id": request.prompt_id}

@app.post(
    f"{API_PREFIX}/prompts/validate",
    summary="Validate template",
    description="Validate a prompt template and extract variables."
)
def validate_template(
    template: str = Body(..., description="Template text to validate")
):
    """Validate a prompt template and extract variables."""
    return registry.validate_template(template)

@app.get(
    f"{API_PREFIX}/prompts/{{prompt_id}}/history", 
    response_model=List[Dict[str, Any]],
    summary="Get prompt history",
    description="Get version history for a prompt's project/task."
)
def get_prompt_history(
    prompt_id: str = Path(..., description="Prompt ID"),
    include_deleted: bool = Query(False, description="Include soft-deleted prompts")
):
    """Get version history for a prompt's project/task."""
    prompt = registry.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
        
    history = registry.get_version_history(
        prompt.project, 
        prompt.task,
        include_deleted=include_deleted
    )
    
    # Convert to dictionaries for serialization
    return [orm_to_dict(p) for p in history]

@app.get(
    f"{API_PREFIX}/prompts/{{prompt_id}}/lineage",
    summary="Get prompt lineage",
    description="Get ancestors and descendants of a prompt."
)
def get_prompt_lineage(
    prompt_id: str = Path(..., description="Prompt ID"),
    include_deleted: bool = Query(False, description="Include soft-deleted prompts")
):
    """Get ancestors and descendants of a prompt."""
    lineage = registry.get_prompt_lineage(prompt_id, include_deleted=include_deleted)
    if not lineage["current"]:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Convert ORM objects to dictionaries for serialization
    result = {
        "current": orm_to_dict(lineage["current"]),
        "ancestors": [orm_to_dict(p) for p in lineage["ancestors"]],
        "descendants": [orm_to_dict(p) for p in lineage["descendants"]]
    }
    return result

@app.post(
    f"{API_PREFIX}/prompts/compare",
    summary="Compare prompts",
    description="Compare two prompt versions to see differences."
)
def compare_prompts(
    request: PromptCompareRequest = Body(..., description="Compare request")
):
    """Compare two prompt versions."""
    comparison = registry.compare_versions(request.prompt_id_1, request.prompt_id_2)
    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])
    return comparison

@app.post(
    f"{API_PREFIX}/prompts/{{prompt_id}}/rollback", 
    response_model=Dict[str, Any],
    summary="Rollback to version",
    description="Create a new version by copying an old version (rollback)."
)
def rollback_prompt(
    prompt_id: str = Path(..., description="Prompt ID to rollback to"),
    updated_by: Optional[str] = Query(None, description="User performing the rollback")
):
    """Rollback to a specific prompt version."""
    new_prompt = registry.rollback_to_version(prompt_id, updated_by=updated_by)
    if not new_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return orm_to_dict(new_prompt)

@app.post(
    f"{API_PREFIX}/prompts/search",
    summary="Search prompts",
    description="Search prompts with filtering and pagination."
)
def search_prompts(
    query: SearchQuery = Body(..., description="Search parameters")
):
    """Search prompts with filtering."""
    results, total = registry.search_prompts(
        query=query.query,
        project=query.project,
        tags=query.tags,
        page=query.page,
        page_size=query.page_size
    )
    
    pages = (total + query.page_size - 1) // query.page_size  # Ceiling division
    
    # Convert to dictionaries for serialization
    result_dicts = [orm_to_dict(p) for p in results]
    
    return {
        "items": result_dicts,
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "pages": pages
    }

@app.post(
    f"{API_PREFIX}/prompts/bulk-tag",
    summary="Bulk tag prompts",
    description="Apply tag operations to multiple prompts at once."
)
def bulk_tag_prompts(
    request: BulkTagRequest = Body(..., description="Bulk tag request")
):
    """Bulk tag operation on multiple prompts."""
    count = registry.bulk_tag_prompts(
        request.prompt_ids,
        request.tags,
        request.operation
    )
    
    return {"modified": count, "operation": request.operation}

# --- Examples Management ---

@app.get(
    f"{API_PREFIX}/prompts/{{prompt_id}}/examples",
    response_model=List[Dict[str, Any]],
    summary="Get prompt examples",
    description="Get input/output examples for a prompt."
)
def get_examples(
    prompt_id: str = Path(..., description="Prompt ID")
):
    """Get examples for a prompt."""
    examples = registry.get_examples(prompt_id)
    return examples  # Already returned as dictionaries by the registry

@app.post(
    f"{API_PREFIX}/prompts/{{prompt_id}}/examples",
    summary="Add example",
    description="Add an input/output example to a prompt."
)
def add_example(
    prompt_id: str = Path(..., description="Prompt ID"),
    example: ExampleIn = Body(..., description="Example data")
):
    """Add an example to a prompt."""
    result = registry.add_example(
        prompt_id,
        example.input,
        example.output,
        example.description
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Prompt not found")
        
    return result.to_dict() if hasattr(result, 'to_dict') else {
        "id": result.id,
        "prompt_id": prompt_id,
        "input": result.input_text,
        "output": result.output_text,
        "description": result.description,
        "created_at": result.created_at.isoformat() if result.created_at else None
    }

# --- Stats & Import/Export ---

@app.get(
    f"{API_PREFIX}/stats",
    summary="Get registry stats",
    description="Get usage statistics about the prompt registry."
)
def get_system_stats():
    """Get registry usage statistics."""
    stats = registry.get_usage_stats()
    return stats

@app.get(
    f"{API_PREFIX}/export",
    summary="Export prompts",
    description="Export prompts to a portable format (JSON/YAML)."
)
def export_prompts(
    project: Optional[str] = Query(None, description="Limit to specific project"),
    format: str = Query("json", description="Export format: 'json' or 'yaml'")
):
    """Export prompts to JSON or YAML."""
    try:
        data = registry.export_prompts(project=project, format=format)
        return Response(
            content=data,
            media_type="application/json" if format == "json" else "application/yaml",
            headers={
                "Content-Disposition": f"attachment; filename=cuebit_export_{datetime.now().strftime('%Y%m%d')}.{format}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    f"{API_PREFIX}/import",
    summary="Import prompts",
    description="Import prompts from JSON or YAML format."
)
def import_prompts(
    request: ImportRequest = Body(..., description="Import request")
):
    """Import prompts from JSON or YAML."""
    results = registry.import_prompts(
        data=request.data,
        format=request.format,
        skip_existing=request.skip_existing
    )
    
    if "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
        
    return results

# --- Health check endpoint ---
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "database_url": registry.db_url, "version": "1.0"}

@app.get("/")
def root():
    """Root endpoint with basic API information."""
    return {
        "message": "Welcome to Cuebit API", 
        "docs": f"{API_PREFIX}/docs",
        "version": "1.0",
        "database_url": registry.db_url
    }