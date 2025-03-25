# cuebit/server.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from cuebit.registry import PromptRegistry, PromptORM

app = FastAPI(
    title="Cuebit Prompt API",
    version="1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

# Enable CORS for external frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = PromptRegistry()

class PromptCreate(BaseModel):
    task: str
    template: str
    tags: Optional[List[str]] = []
    meta: dict
    project: Optional[str] = None

class PromptUpdate(BaseModel):
    new_template: str
    meta: Optional[dict] = None

class PromptOut(BaseModel):
    prompt_id: str
    task: str
    template: str
    version: int
    alias: Optional[str]
    project: Optional[str]
    tags: Optional[str]
    meta: dict
    created_at: str

    class Config:
        orm_mode = True

@app.get("/api/v1/projects", response_model=List[str])
def list_projects():
    return registry.list_projects()

@app.get("/api/v1/projects/{project}/prompts", response_model=List[PromptOut])
def get_project_prompts(project: str):
    return registry.list_prompts_by_project(project)

@app.get("/api/v1/prompts", response_model=List[PromptOut])
def list_prompts():
    return registry.list_prompts()

@app.post("/api/v1/prompts", response_model=PromptOut)
def create_prompt(prompt: PromptCreate):
    return registry.register_prompt(
        task=prompt.task,
        template=prompt.template,
        meta=prompt.meta,
        tags=prompt.tags,
        project=prompt.project,
    )

@app.get("/api/v1/prompts/{prompt_id}", response_model=PromptOut)
def get_prompt(prompt_id: str):
    prompt = registry.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt

@app.put("/api/v1/prompts/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: str, update: PromptUpdate):
    prompt = registry.update_prompt(prompt_id, update.new_template, update.meta)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt

@app.post("/api/v1/prompts/{prompt_id}/alias", response_model=PromptOut)
def alias_prompt(prompt_id: str, alias: str = Query(...)):
    prompt = registry.add_alias(prompt_id, alias)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt