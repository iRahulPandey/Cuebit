# 🚀 Cuebit - Prompt Versioning and Management for GenAI

Cuebit is an open-source, local-first prompt registry and version control system designed for GenAI development teams — complete with a local server, version tracking, aliases, tagging, and an interactive dashboard.

---

## ✨ Features

- 🔐 Prompt version control with auto-increment
- 🏷️ Alias system (e.g. `summarizer-prod` → versioned prompt)
- 🧠 Tags and metadata for organizing prompts
- 📁 Project & Task-based prompt grouping
- 📈 Streamlit-based visual dashboard
- ⚙️ REST API powered by FastAPI (`/api/v1/...`)
- 🔄 Full CLI support (`cuebit serve`)
- 🧪 Prompt template preview and rendering
- 👤 Audit trail: `created_at`, `updated_at`, `updated_by`

---

## 📦 Installation

```bash
pip install -e .  # from source
```

Make sure you have `sqlite3`, `streamlit`, `fastapi`, `sqlalchemy`, and `uvicorn` in your environment.

---

## 🚀 Getting Started

### 🧪 Registering a Prompt

```python
from cuebit.registry import PromptRegistry

registry = PromptRegistry()
registry.register_prompt(
    task="summarization",
    template="Summarize: {input}",
    meta={"model": "gpt-4"},
    tags=["prod"],
    project="bloggen",
    updated_by="alice"
)
```

### 🧭 Setting Aliases

```python
registry.add_alias(prompt_id, "summarizer-prod")
```

### 🔁 Updating a Prompt

```python
registry.update_prompt(
    prompt_id,
    new_template="Summarize concisely: {input}",
    updated_by="bob"
)
```

---

## 🧪 Streamlit Dashboard

```bash
cuebit --host 127.0.0.1 --port 8000  # launches API + UI
```

---

## 📚 API Reference

- `GET /api/v1/projects`
- `GET /api/v1/projects/{project}/prompts`
- `GET /api/v1/prompts`
- `POST /api/v1/prompts`
- `PUT /api/v1/prompts/{prompt_id}`
- `POST /api/v1/prompts/{prompt_id}/alias`

---

## 🛠️ Development

To reinitialize the local SQLite DB (e.g. after schema change):

```bash
rm prompts.db
python example_usage.py  # regenerates DB and adds sample data
```

---

## 📈 Roadmap

- [ ] Soft delete support (archived prompts)
- [ ] Role-based auth
- [ ] Multi-user workspace (SQLite → Postgres)
- [ ] Cloud-hosted Cuebit server
- [ ] Export to LangChain / prompt catalogs

---

## 🤝 Contributing

PRs are welcome! 

---
