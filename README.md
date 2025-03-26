# 🚀 Cuebit - Prompt Versioning and Management for GenAI

Cuebit is an open-source, local-first prompt registry and version control system designed for GenAI development teams — complete with version tracking, version history, lineage tracking, aliases, tagging, and an interactive dashboard.

![alt text](<Cuebit Highlevel Overview.png>)

---

## ✨ Features

- 🔐 **Prompt version control** with full history and lineage tracking
- 🏷️ **Alias system** (e.g. `summarizer-prod` → versioned prompt)
- 🧠 **Tags and metadata** for organizing prompts
- 📁 **Project & Task-based** prompt grouping
- 📋 **Example management** for documenting prompt usage patterns
- 📑 **Template variables** detection and validation
- 🔍 **Version comparison** with visual diffs
- 📈 **Streamlit-based** visual dashboard
- ⚙️ **REST API** powered by FastAPI (`/api/v1/...`)
- 🔄 **Full CLI support** for automation
- 🧪 **Prompt template preview** and rendering
- 👤 **Audit trail**: `created_at`, `updated_at`, `updated_by`
- 📤 **Import/Export** functionality for backup and sharing

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/iRahulPandey/Cuebit.git
cd cuebit

# Install the package
pip install -e .
```

Make sure you have the required dependencies:

```bash
pip install fastapi uvicorn sqlalchemy streamlit pandas altair pydantic
```

---

## 🚀 Getting Started

### 🧪 Registering a Prompt

```python
from cuebit.registry import PromptRegistry

registry = PromptRegistry()
registry.register_prompt(
    task="summarization",
    template="Summarize: {input}",
    meta={"model": "gpt-4", "temperature": 0.7},
    tags=["prod"],
    project="bloggen",
    updated_by="alice",
    examples=[{
        "input": "The quick brown fox jumps over the lazy dog.",
        "output": "A fox jumps over a dog.",
        "description": "Basic example"
    }]
)
```

### 🧭 Setting Aliases

```python
registry.add_alias(prompt_id, "summarizer-prod")
```

### 🔁 Updating a Prompt (Creates a new version)

```python
registry.update_prompt(
    prompt_id,
    new_template="Summarize concisely: {input}",
    updated_by="bob"
)
```

### 📋 Adding Examples

```python
registry.add_example(
    prompt_id,
    input_text="Climate change is a global challenge...",
    output_text="Climate change poses worldwide risks requiring immediate action.",
    description="Climate topic example"
)
```

### 🔍 Comparing Versions

```python
comparison = registry.compare_versions(prompt_id_1, prompt_id_2)
print(f"Template differences: {len(comparison['template_diff'])} lines")
print(f"Added tags: {comparison['tags_changes']['added']}")
```

### 🔄 Rendering Prompts

```python
rendered = registry.render_prompt(
    prompt_id,
    {"input": "Text to summarize..."}
)
```

---

## 🧪 Streamlit Dashboard

```bash
cuebit serve --host 127.0.0.1 --port 8000  # launches API + UI
```

The dashboard provides:
- Project and prompt browsing
- Visual prompt builder with variable detection
- Version history with visual diffs
- Import/Export functionality
- Usage statistics

---

## 🔧 Command Line Interface

```bash
# Start the server and dashboard
cuebit serve

# List all projects
cuebit list projects

# List prompts in a project
cuebit list prompts --project my-project

# Create a new prompt
cuebit create prompt --task summarization \
    --template "Summarize: {input}" \
    --project my-project --tags "prod,gpt-4"

# Set an alias
cuebit set-alias  summarizer-prod

# Render a prompt with variables
cuebit render --alias summarizer-prod \
    --vars '{"input":"Text to summarize"}'

# Export prompts to JSON
cuebit export --format json --file exports.json
```

---

## 📚 API Reference

- `GET /api/v1/projects` - List all projects
- `GET /api/v1/projects/{project}/prompts` - List prompts in a project
- `GET /api/v1/prompts` - List all prompts (with pagination and filtering)
- `POST /api/v1/prompts` - Create a new prompt
- `GET /api/v1/prompts/{prompt_id}` - Get a specific prompt
- `PUT /api/v1/prompts/{prompt_id}` - Update a prompt (creates new version)
- `POST /api/v1/prompts/{prompt_id}/alias` - Set an alias for a prompt
- `GET /api/v1/prompts/alias/{alias}` - Get a prompt by its alias
- `POST /api/v1/prompts/render` - Render a prompt with variables
- `GET /api/v1/prompts/{prompt_id}/history` - Get version history
- `POST /api/v1/prompts/compare` - Compare two prompt versions
- `POST /api/v1/prompts/{prompt_id}/rollback` - Rollback to a previous version
- `DELETE /api/v1/prompts/{prompt_id}` - Delete a prompt (soft by default)
- `GET /api/v1/export` - Export prompts
- `POST /api/v1/import` - Import prompts

![alt text](<Cuebit Detailed Overview.png>)

---

## 📁 Project Structure

```
cuebit/
├── cuebit/
│   ├── __init__.py
│   ├── registry.py   # Core prompt management and versioning
│   ├── server.py     # FastAPI server and API endpoints
│   └── cli.py        # Command-line interface
├── cuebit_dashboard.py  # Streamlit dashboard
├── pyproject.toml    # Project metadata
├── README.md
└── examples          # Example
│   ├── e2e_example.py
│   ├── register_prompts.py
│   └── summarization_app.py 
```

---

## 🛠️ Development

To reinitialize the local SQLite DB (e.g. after schema change):

```bash
rm prompts.db
python example.py  # regenerates DB and adds sample data
```

---