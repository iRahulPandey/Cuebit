# example_usage.py — Full Showcase of Cuebit Capabilities
from cuebit.registry import PromptRegistry
import json
from pprint import pprint

# Initialize registry
registry = PromptRegistry()

# === 1. Register prompts in different projects ===
p1 = registry.register_prompt(
    task="summarization",
    template="Summarize this article: {input}",
    meta={"model": "gpt-4", "temp": 0.7},
    tags=["prod", "nlp"],
    project="blog_summarizer"
)

p2 = registry.register_prompt(
    task="summarization",
    template="Give a concise summary of: {input}",
    meta={"model": "gpt-4", "temp": 0.6},
    tags=["test", "nlp"],
    project="blog_summarizer"
)

p3 = registry.register_prompt(
    task="qa",
    template="Answer the question based on context: {input}",
    meta={"model": "claude", "temp": 0.5},
    tags=["prod", "qa"],
    project="question_answering"
)

# === 2. Set aliases ===
registry.add_alias(p1.prompt_id, "summarizer-prod")
registry.add_alias(p3.prompt_id, "qa-prod")

# === 3. List all prompts ===
all_prompts = registry.list_prompts()
print("\nAll Prompts:")
for p in all_prompts:
    print(f"[{p.project}] v{p.version} - {p.task} | alias: {p.alias}")

# === 4. Get prompt by alias ===
alias_lookup = registry.get_prompt_by_alias("summarizer-prod")
print(f"\nPrompt resolved from alias 'summarizer-prod':\n{alias_lookup.template}")

# === 5. Get prompts by project ===
project_prompts = registry.list_prompts_by_project("blog_summarizer")
print("\nBlog Summarizer Prompts:")
for p in project_prompts:
    print(f"v{p.version} | task: {p.task} | tags: {p.tags}")

# === 6. Update a prompt (creates new version) ===
updated = registry.update_prompt(
    prompt_id=p1.prompt_id,
    new_template="Summarize this in 1 sentence: {input}",
    meta={"notes": "made it tighter"}
)

# Refresh session to avoid DetachedInstanceError
updated_fetched = registry.get_prompt(p1.prompt_id)
print(f"\nUpdated Prompt to v{updated_fetched.version}: {updated_fetched.template}")

# === 7. List all projects ===
projects = registry.list_projects()
print("\nProjects:", projects)

# === 8. Tag statistics ===
tag_stats = registry.get_tag_stats()
print("\nTag Stats:")
pprint(tag_stats)

# === 9. Test rendering a prompt ===
input_text = "OpenAI released a new model."
rendered = alias_lookup.template.replace("{input}", input_text)
print(f"\nRendered Prompt (via alias):\n{rendered}")

# === 10. Delete a specific prompt version ===
# print("\nDeleting version 1 from blog_summarizer")
# deleted = registry.delete_prompt_by_id(p1.prompt_id)
# print("Deleted:" if deleted else "Failed to delete")

# === 11. Delete all prompts under a project ===
# print("\nDeleting all prompts from project: question_answering")
# deleted_count = registry.delete_project("question_answering")
# print(f"Deleted {deleted_count} prompts")

# === 12. Delete all versions of a task in a project ===
# print("\nDeleting all prompts of task 'summarization' in project 'blog_summarizer'")
# deleted_task_count = registry.delete_prompts_by_project_task("blog_summarizer", "summarization")
# print(f"Deleted {deleted_task_count} prompts")