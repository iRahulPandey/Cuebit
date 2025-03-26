# comprehensive_example.py
"""
This example demonstrates the full capabilities of Cuebit's enhanced features.
Run this script to see Cuebit in action with examples of:
- Creating prompts with examples and metadata
- Version tracking and lineage
- Aliasing
- Rendering prompts
- Comparing versions
- Exporting and importing
- And more!
"""

import json
import os
from pprint import pprint
from datetime import datetime

# Import the registry
from cuebit.registry import PromptRegistry

# Initialize registry (creates database if it doesn't exist)
registry = PromptRegistry()

# Clear the existing database for this demo
import sqlite3
try:
    os.remove("prompts.db")
    print("Previous database removed. Starting fresh.")
except FileNotFoundError:
    print("Creating a new database.")
registry = PromptRegistry()

print("\n" + "="*50)
print("Cuebit Enhanced Example Script")
print("="*50)

# --------------------------------------------------
# 1. Creating Prompts in Different Projects
# --------------------------------------------------
print("\n1. CREATING PROMPTS IN DIFFERENT PROJECTS")
print("-" * 40)

# Create a summarization prompt with examples
summary_prompt = registry.register_prompt(
    task="summarization",
    template="Summarize this article in a concise way:\n\n{input}",
    meta={
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 300,
        "purpose": "Generate short summaries for blog articles"
    },
    tags=["prod", "blog", "summarization"],
    project="content-generator",
    updated_by="alice",
    examples=[
        {
            "input": "The quick brown fox jumps over the lazy dog. The dog didn't move as the agile fox demonstrated its athletic prowess. The fox continued on its journey through the forest.",
            "output": "A quick fox jumped over a lazy dog and continued through the forest.",
            "description": "Simple summarization example"
        }
    ]
)

print(f"Created summarization prompt (ID: {summary_prompt.prompt_id})")

# Create a QA prompt 
qa_prompt = registry.register_prompt(
    task="question-answering",
    template="Answer the following question based on the given context:\n\nContext: {context}\n\nQuestion: {question}",
    meta={
        "model": "claude-3-opus",
        "temperature": 0.3,
        "purpose": "Answer questions based on provided context"
    },
    tags=["prod", "customer-support", "qa"],
    project="customer-support",
    updated_by="bob",
    examples=[
        {
            "input": "Context: Our return policy allows items to be returned within 30 days of purchase with a receipt. All electronics have a 14-day return window.\nQuestion: Can I return headphones after 20 days?",
            "output": "No, you cannot return headphones after 20 days. While our general return policy is 30 days, all electronics (including headphones) have a shorter 14-day return window.",
            "description": "Return policy question"
        }
    ]
)

print(f"Created QA prompt (ID: {qa_prompt.prompt_id})")

# Create a translation prompt
translation_prompt = registry.register_prompt(
    task="translation",
    template="Translate the following {source_language} text to {target_language}:\n\n{text}",
    meta={
        "model": "gpt-4",
        "temperature": 0.3,
        "purpose": "Translate text between languages"
    },
    tags=["dev", "translation"],
    project="localization",
    updated_by="charlie",
    examples=[
        {
            "input": "source_language: English\ntarget_language: Spanish\ntext: Hello, how are you today?",
            "output": "Hola, ¿cómo estás hoy?",
            "description": "English to Spanish"
        }
    ]
)

print(f"Created translation prompt (ID: {translation_prompt.prompt_id})")

# Create an email generator prompt
email_prompt = registry.register_prompt(
    task="email-generation",
    template="Write a professional email with the following parameters:\n\nTone: {tone}\nPurpose: {purpose}\nRecipient: {recipient}\nKey points:\n{key_points}",
    meta={
        "model": "claude-3-opus",
        "temperature": 0.7,
        "purpose": "Generate professional emails"
    },
    tags=["prod", "email", "business"],
    project="business-writing",
    updated_by="dave",
    examples=[
        {
            "input": "tone: Friendly\npurpose: Meeting follow-up\nrecipient: Client\nkey_points: - Thank them for the meeting\n- Summarize key decisions\n- Propose next steps\n- Ask for confirmation",
            "output": "Dear [Client],\n\nThank you for taking the time to meet with us yesterday. It was great to discuss the project in detail.\n\nTo summarize what we agreed upon:\n- Timeline: 6 weeks for completion\n- Budget: $10,000\n- Deliverables: Website redesign with 5 pages\n\nOur team will begin work next Monday. We propose a check-in call every Friday at 2 PM to share progress.\n\nCould you please confirm these details are correct?\n\nBest regards,\n[Your Name]",
            "description": "Meeting follow-up email"
        }
    ]
)

print(f"Created email prompt (ID: {email_prompt.prompt_id})")

# --------------------------------------------------
# 2. Setting Aliases
# --------------------------------------------------
print("\n2. SETTING ALIASES")
print("-" * 40)

# Set aliases for production use
registry.add_alias(summary_prompt.prompt_id, "summarizer-prod")
registry.add_alias(qa_prompt.prompt_id, "qa-prod")
registry.add_alias(email_prompt.prompt_id, "email-prod")

print("Set aliases:")
print("- 'summarizer-prod' -> summarization prompt")
print("- 'qa-prod' -> question-answering prompt")
print("- 'email-prod' -> email generation prompt")

# --------------------------------------------------
# 3. Retrieving Prompts
# --------------------------------------------------
print("\n3. RETRIEVING PROMPTS")
print("-" * 40)

# Get prompt by ID
retrieved_prompt = registry.get_prompt(summary_prompt.prompt_id)
print(f"Retrieved by ID: {retrieved_prompt.task} (v{retrieved_prompt.version})")

# Get prompt by alias
alias_prompt = registry.get_prompt_by_alias("summarizer-prod")
print(f"Retrieved by alias: {alias_prompt.task} (v{alias_prompt.version})")

# List prompts by project
project_prompts = registry.list_prompts_by_project("content-generator")
print(f"Found {len(project_prompts)} prompts in 'content-generator' project")

# List all projects
projects = registry.list_projects()
print(f"All projects: {', '.join(projects)}")

# Get tag statistics
tag_stats = registry.get_tag_stats()
print("Tag usage:")
for tag, count in tag_stats.most_common():
    print(f"- {tag}: {count}")

# --------------------------------------------------
# 4. Updating Prompts (Creating New Versions)
# --------------------------------------------------
print("\n4. UPDATING PROMPTS (CREATING NEW VERSIONS)")
print("-" * 40)

# Update summary prompt with a better template
summary_v2 = registry.update_prompt(
    prompt_id=summary_prompt.prompt_id,
    new_template="Provide a concise summary of this article in 2-3 sentences:\n\n{input}",
    meta={
        "model": "gpt-4",
        "temperature": 0.5,  # Reduced temperature for more focused output
        "max_tokens": 250,   # Slightly reduced token count
        "purpose": "Generate short summaries for blog articles",
        "version_notes": "Improved directive for conciseness"
    },
    updated_by="alice",
    tags=["prod", "blog", "summarization", "concise"],  # Added 'concise' tag
    examples=[
        {
            "input": "Climate change is a global challenge that requires immediate action. The Earth's average temperature has increased by about 1 degree Celsius since pre-industrial times, primarily due to human activities like burning fossil fuels. This warming is causing more extreme weather events, rising sea levels, and disruption to ecosystems worldwide. Scientists warn that limiting warming to 1.5 degrees Celsius would significantly reduce these risks.",
            "output": "Climate change, driven primarily by human activities like fossil fuel use, has increased Earth's temperature by 1°C since pre-industrial times. This warming is causing extreme weather, rising seas, and ecosystem disruption, with scientists recommending limiting warming to 1.5°C to reduce these effects.",
            "description": "Climate change summary example"
        }
    ]
)

print(f"Updated summarization prompt: v{summary_v2.version} (ID: {summary_v2.prompt_id})")
print(f"New template: {summary_v2.template}")

# Update it once more with another refinement
summary_v3 = registry.update_prompt(
    prompt_id=summary_v2.prompt_id,
    new_template="Summarize this article in 1-2 sentences using simple, clear language:\n\n{input}",
    meta={
        "model": "gpt-4",
        "temperature": 0.4,
        "max_tokens": 200,
        "purpose": "Generate very short summaries for blog articles",
        "version_notes": "Simplified output further, specified sentence count"
    },
    updated_by="ellie",
    tags=["prod", "blog", "summarization", "concise", "simple-language"]
)

print(f"Updated summarization prompt again: v{summary_v3.version} (ID: {summary_v3.prompt_id})")

# Update the alias to point to the latest version
registry.add_alias(summary_v3.prompt_id, "summarizer-prod", overwrite=True)
print("Updated 'summarizer-prod' alias to point to v3")

# --------------------------------------------------
# 5. Prompt Lineage and History
# --------------------------------------------------
print("\n5. PROMPT LINEAGE AND HISTORY")
print("-" * 40)

# Get version history for a project/task
history = registry.get_version_history("analytics", "data-analysis")
print(f"Version history after rollback:")
for item in history:
    p = item["prompt"]
    parent = ""
    if item["parent_info"]:
        parent = f" (based on v{item['parent_info']['version']})"
    
    print(f"- v{p.version} by {p.updated_by}{parent}")

# Get lineage for a specific prompt
lineage = registry.get_prompt_lineage(summary_v2.prompt_id)
print(f"\nLineage for summarization v2:")
print(f"- Ancestors: {len(lineage['ancestors'])}")
for p in lineage['ancestors']:
    print(f"  * v{p.version} (ID: {p.prompt_id})")
print(f"- Descendants: {len(lineage['descendants'])}")
for p in lineage['descendants']:
    print(f"  * v{p.version} (ID: {p.prompt_id})")

# --------------------------------------------------
# 6. Comparing Versions
# --------------------------------------------------
print("\n6. COMPARING VERSIONS")
print("-" * 40)

# Compare v1 and v3 of the summarization prompt
comparison = registry.compare_versions(summary_prompt.prompt_id, summary_v3.prompt_id)

print("Template differences:")
for line in comparison["template_diff"][:5]:  # Show first 5 lines only
    print(f"  {line}")

print("\nMetadata changes:")
if comparison["meta_changes"]["changed"]:
    for key, change in comparison["meta_changes"]["changed"].items():
        print(f"  - {key}: {change['from']} -> {change['to']}")

print("\nTag changes:")
if comparison["tags_changes"]["added"]:
    print(f"  - Added tags: {', '.join(comparison['tags_changes']['added'])}")

# --------------------------------------------------
# 7. Rendering Prompts with Variables
# --------------------------------------------------
print("\n7. RENDERING PROMPTS WITH VARIABLES")
print("-" * 40)

# Render the summarization prompt
summary_input = "Artificial intelligence (AI) is transforming industries across the global economy. From healthcare to finance, transportation to retail, AI technologies are automating tasks, providing new insights, and creating new capabilities. While concerns exist about job displacement and ethical implications, proponents argue that AI will ultimately create more jobs than it eliminates and that proper governance can address ethical challenges."

rendered_summary = registry.render_prompt(
    summary_v3.prompt_id,
    {"input": summary_input}
)

print("Rendered summarization prompt:")
print("-" * 20)
print(rendered_summary)
print("-" * 20)

# Render the translation prompt
translation_rendered = registry.render_prompt(
    translation_prompt.prompt_id,
    {
        "source_language": "English",
        "target_language": "French",
        "text": "Welcome to our online store. We offer free shipping on all orders over $50."
    }
)

print("\nRendered translation prompt:")
print("-" * 20)
print(translation_rendered)
print("-" * 20)

# --------------------------------------------------
# 8. Template Validation
# --------------------------------------------------
print("\n8. TEMPLATE VALIDATION")
print("-" * 40)

# Validate a valid template
valid_template = "Generate a product description for {product_name} with key features: {features}"
validation = registry.validate_template(valid_template)
print(f"Valid template validation:")
print(f"- Is valid: {validation['is_valid']}")
print(f"- Variables: {', '.join(validation['variables'])}")
print(f"- Warnings: {len(validation['warnings'])}")

# Validate a template with issues
invalid_template = "This template has an unclosed bracket: {product_name"
validation = registry.validate_template(invalid_template)
print(f"\nInvalid template validation:")
print(f"- Is valid: {validation['is_valid']}")
print(f"- Variables: {', '.join(validation['variables'])}")
print(f"- Warnings: {', '.join(validation['warnings'])}")

# --------------------------------------------------
# 9. Working with Examples
# --------------------------------------------------
print("\n9. WORKING WITH EXAMPLES")
print("-" * 40)

# Add another example to the email prompt
registry.add_example(
    email_prompt.prompt_id,
    input_text="tone: Formal\npurpose: Job application\nrecipient: Hiring Manager\nkey_points: - Express interest in software developer position\n- Highlight 5 years of Python experience\n- Mention Master's degree in Computer Science\n- Request interview opportunity",
    output_text="Dear Hiring Manager,\n\nI am writing to express my strong interest in the Software Developer position at [Company Name] as advertised on your website.\n\nWith five years of professional experience developing Python applications and a Master's degree in Computer Science, I believe I have the technical expertise and background that would make me a valuable addition to your team.\n\nI would welcome the opportunity to discuss how my skills align with your needs in an interview. I am available at your convenience and can be reached at [phone number] or [email].\n\nThank you for considering my application. I look forward to the possibility of working with your team.\n\nSincerely,\n[Your Name]",
    description="Job application email"
)

# Get examples for the email prompt
examples = registry.get_examples(email_prompt.prompt_id)
print(f"Email prompt has {len(examples)} examples:")
for i, ex in enumerate(examples):
    print(f"- Example {i+1}: {ex['description']}")
    print(f"  Input length: {len(ex['input'])} chars")
    print(f"  Output length: {len(ex['output'])} chars")

# --------------------------------------------------
# 10. Soft Delete and Restore
# --------------------------------------------------
print("\n10. SOFT DELETE AND RESTORE")
print("-" * 40)

# Soft delete the translation prompt
registry.soft_delete_prompt(translation_prompt.prompt_id, deleted_by="admin")
print(f"Soft-deleted translation prompt (ID: {translation_prompt.prompt_id})")

# Try to retrieve the deleted prompt (with and without include_deleted)
deleted_prompt = registry.get_prompt(translation_prompt.prompt_id)
print(f"Retrieved without include_deleted: {deleted_prompt}")

deleted_prompt = registry.get_prompt(translation_prompt.prompt_id, include_deleted=True)
print(f"Retrieved with include_deleted: {deleted_prompt.task if deleted_prompt else None}")

# Restore the prompt
registry.restore_prompt(translation_prompt.prompt_id)
print(f"Restored translation prompt")

# Verify it's back
restored_prompt = registry.get_prompt(translation_prompt.prompt_id)
print(f"Retrieved after restore: {restored_prompt.task if restored_prompt else None}")

# --------------------------------------------------
# 11. Bulk Operations
# --------------------------------------------------
print("\n11. BULK OPERATIONS")
print("-" * 40)

# Bulk tag prompts
prompt_ids = [summary_prompt.prompt_id, summary_v2.prompt_id, summary_v3.prompt_id]
modified = registry.bulk_tag_prompts(prompt_ids, ["important", "demo"], operation="add")
print(f"Added tags to {modified} prompts")

# Delete all prompts in a project (soft delete)
count = registry.delete_project("localization", use_soft_delete=True)
print(f"Soft-deleted {count} prompts from 'localization' project")

# --------------------------------------------------
# 12. Export and Import
# --------------------------------------------------
print("\n12. EXPORT AND IMPORT")
print("-" * 40)

# Export all prompts to JSON
exported = registry.export_prompts(format="json")
export_length = len(exported)
print(f"Exported {export_length} bytes of JSON data")

# Save to a file for demonstration
with open("exported_prompts.json", "w") as f:
    f.write(exported)
print("Saved export to 'exported_prompts.json'")

# Import the data back (to demonstrate the capability)
import_results = registry.import_prompts(exported, format="json", skip_existing=True)
print(f"Import results:")
print(f"- Total: {import_results['total']}")
print(f"- Imported: {import_results['imported']}")
print(f"- Skipped: {import_results['skipped']}")

# --------------------------------------------------
# 13. Registry Statistics
# --------------------------------------------------
print("\n13. REGISTRY STATISTICS")
print("-" * 40)

stats = registry.get_usage_stats()
print(f"Registry statistics:")
print(f"- Total prompts: {stats['total_prompts']}")
print(f"- Active prompts: {stats['active_prompts']}")
print(f"- Deleted prompts: {stats['deleted_prompts']}")
print(f"- Projects: {stats['total_projects']}")
print(f"- Prompts with aliases: {stats['prompts_with_aliases']}")
print(f"- Total examples: {stats.get('total_examples', 0)}")

# --------------------------------------------------
# 14. ROLLBACK DEMONSTRATION
# --------------------------------------------------
print("\n14. ROLLBACK DEMONSTRATION")
print("-" * 40)

# Create a new prompt for demonstration
data_prompt = registry.register_prompt(
    task="data-analysis",
    template="Analyze the following data and provide insights:\n\n{data}",
    meta={"model": "gpt-4", "temperature": 0.2},
    tags=["analysis", "data"],
    project="analytics",
    updated_by="frank"
)

print(f"Created data analysis prompt v1 (ID: {data_prompt.prompt_id})")

# Update it with a new version
data_prompt_v2 = registry.update_prompt(
    prompt_id=data_prompt.prompt_id,
    new_template="Provide a detailed analysis of this data with 3 key insights:\n\n{data}",
    meta={"model": "gpt-4", "temperature": 0.3},
    updated_by="grace"
)

print(f"Updated to v2 (ID: {data_prompt_v2.prompt_id})")

# Roll back to v1
rollback = registry.rollback_to_version(data_prompt.prompt_id, updated_by="admin")
print(f"Rolled back to create v3 based on v1 (ID: {rollback.prompt_id})")

# Show the history - Safe approach that handles both ORM objects and dictionaries
history = registry.get_version_history("analytics", "data-analysis")
print(f"Version history after rollback:")
for p in history:
    # Safely handle different data types that might be returned
    try:
        # Attempt to get version and updated_by - handles both ORM objects and dicts
        if isinstance(p, dict):
            version = p.get('version', 'unknown')
            updated_by = p.get('updated_by', 'unknown')
            parent_id = p.get('parent_id')
        else:
            # Assuming ORM object
            version = p.version
            updated_by = p.updated_by or 'unknown'
            parent_id = p.parent_id
            
        # Simple output without trying to access parent
        print(f"- v{version} by {updated_by}")
        
    except Exception as e:
        # Fallback for any unexpected structure
        print(f"- Version data (format error: {e})")

# --------------------------------------------------
# 15. Search Functionality
# --------------------------------------------------
print("\n15. SEARCH FUNCTIONALITY")
print("-" * 40)

# Search for prompts with "concise" in the template or metadata
search_results, total = registry.search_prompts("concise")
print(f"Search for 'concise' found {total} results:")
for p in search_results:
    print(f"- {p.task} v{p.version} (ID: {p.prompt_id})")

# Search with tag filtering
search_results, total = registry.search_prompts(
    "summary", 
    tags=["concise", "prod"]
)
print(f"\nSearch for 'summary' with tags 'concise' and 'prod' found {total} results:")
for p in search_results:
    print(f"- {p.task} v{p.version} (ID: {p.prompt_id})")

print("\n" + "="*50)
print("Example Complete! Summary:")
print("="*50)
print(f"- Created {stats['total_prompts']} prompts across {stats['total_projects']} projects")
print(f"- Demonstrated all core Cuebit features")
print(f"- Exported data to 'exported_prompts.json'")
print("="*50)