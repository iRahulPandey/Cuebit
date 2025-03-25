from cuebit.registry import PromptRegistry
import json
from pprint import pprint

# Initialize registry
registry = PromptRegistry()

# === 12. Delete all versions of a task in a project ===
print("\nDeleting all prompts of task 'summarization' in project 'blog_summarizer'")
deleted_task_count = registry.delete_prompts_by_project_task("blog_summarizer", "summarization")
print(f"Deleted {deleted_task_count} prompts")