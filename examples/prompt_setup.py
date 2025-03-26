"""
Example script to set up prompts for demonstration purposes.

This script creates a set of example prompts in the registry.
Run this script before using the streamlit_app.py example.
"""

import os
from cuebit.registry import PromptRegistry

# Initialize registry
registry = PromptRegistry()

def create_example_prompts():
    """Create a set of example prompts for demonstration."""
    print(f"Using database at: {registry.db_url}")

    # Check if we already have a summarizer prompt
    existing = registry.get_prompt_by_alias("summarizer-prod")
    if existing:
        print(f"Summarizer prompt already exists with ID: {existing.prompt_id}")
        return existing
        
    # Create a summarization prompt
    summary_prompt = registry.register_prompt(
        task="summarization",
        template="Summarize this text in a clear, concise way: {input_text}",
        meta={
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 300,
            "purpose": "Generate concise summaries"
        },
        tags=["prod", "summarization"],
        project="text-summarizer",
        updated_by="setup_script",
        examples=[
            {
                "input": "The quick brown fox jumps over the lazy dog. The dog didn't move as the agile fox demonstrated its athletic prowess. The fox continued on its journey through the forest.",
                "output": "A fox jumped over a lazy dog and continued through a forest.",
                "description": "Basic summarization example"
            }
        ]
    )
    
    # Set an alias for easy reference
    registry.add_alias(summary_prompt.prompt_id, "summarizer-prod")
    
    print(f"Created summarization prompt v1 with ID: {summary_prompt.prompt_id}")
    
    # Create a second version with a more specific template
    summary_v2 = registry.update_prompt(
        prompt_id=summary_prompt.prompt_id,
        new_template="Provide a concise summary of this text in 2-3 sentences:\n\n{input_text}",
        meta={
            "model": "gpt-4",
            "temperature": 0.5,  # Lower temperature for more focused output
            "max_tokens": 250,
            "purpose": "Generate short summaries with specific length guidance"
        },
        updated_by="setup_script",
        tags=["prod", "summarization", "concise"],
        examples=[
            {
                "input": "Climate change is a global challenge that requires immediate action. The Earth's average temperature has increased by about 1 degree Celsius since pre-industrial times, primarily due to human activities like burning fossil fuels. This warming is causing more extreme weather events, rising sea levels, and disruption to ecosystems worldwide. Scientists warn that limiting warming to 1.5 degrees Celsius would significantly reduce these risks.",
                "output": "Climate change, driven by human activities, has increased Earth's temperature by 1°C since pre-industrial times. This warming causes extreme weather, rising sea levels, and ecosystem disruption, with scientists recommending limiting warming to 1.5°C to reduce impacts.",
                "description": "Climate change summary example"
            }
        ]
    )
    
    print(f"Created summarization prompt v2 with ID: {summary_v2.prompt_id}")
    
    # Create a third version focused on extreme brevity
    summary_v3 = registry.update_prompt(
        prompt_id=summary_v2.prompt_id,
        new_template="Summarize this article in 1-2 sentences using simple, clear language:\n\n{input_text}",
        meta={
            "model": "gpt-4",
            "temperature": 0.4,
            "max_tokens": 200,
            "purpose": "Generate very short summaries with simple language"
        },
        updated_by="setup_script",
        tags=["prod", "summarization", "concise", "simple-language"]
    )
    
    print(f"Created summarization prompt v3 with ID: {summary_v3.prompt_id}")
    
    # Switch the alias to point to v3
    registry.add_alias(summary_v3.prompt_id, "summarizer-prod", overwrite=True)
    print("Updated 'summarizer-prod' alias to point to v3")
    
    # Return the latest version
    return summary_v3

def create_translation_prompt():
    """Create a translation prompt example."""
    # Check if we already have a translation prompt
    existing = registry.get_prompt_by_alias("translator-prod")
    if existing:
        print(f"Translation prompt already exists with ID: {existing.prompt_id}")
        return existing
        
    # Create a translation prompt
    translation_prompt = registry.register_prompt(
        task="translation",
        template="Translate the following {source_language} text to {target_language}:\n\n{text}",
        meta={
            "model": "gpt-4",
            "temperature": 0.3,
            "purpose": "Translate text between languages"
        },
        tags=["prod", "translation"],
        project="language-tools",
        updated_by="setup_script",
        examples=[
            {
                "input": "source_language: English\ntarget_language: Spanish\ntext: Hello, how are you today?",
                "output": "Hola, ¿cómo estás hoy?",
                "description": "English to Spanish"
            }
        ]
    )
    
    # Set an alias
    registry.add_alias(translation_prompt.prompt_id, "translator-prod")
    
    print(f"Created translation prompt with ID: {translation_prompt.prompt_id}")
    return translation_prompt

def create_qa_prompt():
    """Create a question-answering prompt example."""
    # Check if we already have a QA prompt
    existing = registry.get_prompt_by_alias("qa-prod")
    if existing:
        print(f"QA prompt already exists with ID: {existing.prompt_id}")
        return existing
        
    # Create a QA prompt
    qa_prompt = registry.register_prompt(
        task="question-answering",
        template="Answer the following question based on the given context:\n\nContext: {context}\n\nQuestion: {question}",
        meta={
            "model": "gpt-4",
            "temperature": 0.2,
            "purpose": "Answer questions based on provided context"
        },
        tags=["prod", "question-answering"],
        project="knowledge-base",
        updated_by="setup_script",
        examples=[
            {
                "input": "Context: Our return policy allows items to be returned within 30 days of purchase with a receipt. All electronics have a 14-day return window.\nQuestion: Can I return headphones after 20 days?",
                "output": "No, you cannot return headphones after 20 days. While our general return policy is 30 days, all electronics (including headphones) have a shorter 14-day return window.",
                "description": "Return policy question"
            }
        ]
    )
    
    # Set an alias
    registry.add_alias(qa_prompt.prompt_id, "qa-prod")
    
    print(f"Created QA prompt with ID: {qa_prompt.prompt_id}")
    return qa_prompt

if __name__ == "__main__":
    # Create all example prompts
    create_example_prompts()
    create_translation_prompt()
    create_qa_prompt()
    
    # Show registry stats
    stats = registry.get_usage_stats()
    print("\nRegistry Statistics:")
    print(f"- Total prompts: {stats['total_prompts']}")
    print(f"- Active prompts: {stats['active_prompts']}")
    print(f"- Total projects: {stats['total_projects']}")
    print(f"- Prompts with aliases: {stats['prompts_with_aliases']}")
    
    print("\nSetup complete! You can now run the example apps.")