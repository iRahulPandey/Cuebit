from cuebit.registry import PromptRegistry

def setup_summarization_prompts():
    """
    Set up initial summarization prompts in the Cuebit registry with comprehensive details.
    """
    # Initialize the registry
    registry = PromptRegistry()

    # Create the first summarization prompt
    summary_prompt = registry.register_prompt(
        task="text-summarization",
        template="""Provide a concise and clear summary of the following text. 
Follow these guidelines:
- Capture the main thesis or central argument
- Highlight 2-3 key supporting points
- Maintain the original text's tone and key nuances
- Aim for 3-5 sentences in length

Text to summarize:
{input_text}

Summary:""",
        meta={
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 300,
            "purpose": "Generate short, informative summaries",
            "domain": "general",
            "complexity_level": "intermediate",
            "output_format": "paragraph",
            "quality_metrics": {
                "conciseness": "high",
                "clarity": "high",
                "information_retention": "high"
            }
        },
        tags=["prod", "summarization", "concise", "general-purpose"],
        project="text-summarizer",
        updated_by="content-team",
        examples=[
            {
                "input": "Artificial intelligence is revolutionizing multiple industries, from healthcare to finance. Machine learning algorithms can now detect diseases with greater accuracy than human experts, predict financial market trends, and even drive autonomous vehicles. Despite these advancements, ethical concerns remain about job displacement and potential misuse of AI technologies.",
                "output": "Artificial intelligence is transforming industries like healthcare, finance, and transportation through advanced machine learning algorithms. These technologies can outperform human experts in tasks such as disease detection and market prediction. However, the rapid advancement of AI also raises significant ethical questions about job displacement and potential technological misuse.",
                "description": "Tech innovation and AI summary example"
            },
            {
                "input": "Climate change represents one of the most significant challenges facing humanity in the 21st century. Rising global temperatures are causing more frequent and severe weather events, including hurricanes, wildfires, and prolonged droughts. Scientists argue that immediate and substantial reductions in carbon emissions are crucial to mitigate the most catastrophic potential outcomes.",
                "output": "Climate change poses an unprecedented global challenge, characterized by increasing frequency and severity of extreme weather events. Scientific consensus emphasizes the urgent need for significant carbon emission reductions to prevent potentially catastrophic environmental consequences. The impacts are already visible through intensified hurricanes, wildfires, and prolonged drought conditions.",
                "description": "Climate change impact summary"
            }
        ]
    )

    # Create a second, more refined version
    summary_v2 = registry.update_prompt(
        prompt_id=summary_prompt.prompt_id,
        new_template="""Create a comprehensive yet concise summary of the following text. 
Your summary should:
- Extract the core message or central argument
- Identify and summarize the most critical supporting points
- Provide context and potential implications
- Maintain academic or professional tone
- Limit to 4-6 sentences

Text to analyze:
{input_text}

Structured Summary:""",
        meta={
            "model": "gpt-4",
            "temperature": 0.5,
            "max_tokens": 350,
            "purpose": "Generate nuanced, context-aware summaries",
            "domain": "academic-professional",
            "complexity_level": "advanced",
            "output_format": "structured-paragraph",
            "quality_metrics": {
                "depth": "high",
                "analytical_insight": "high",
                "context_preservation": "very-high"
            }
        },
        updated_by="senior-editor",
        tags=["prod", "summarization", "nuanced", "advanced", "professional"],
        examples=[
            {
                "input": "Quantum computing represents a paradigm shift in computational technology. Unlike classical computers that use binary bits, quantum computers leverage quantum mechanics principles like superposition and entanglement. Recent breakthroughs by companies like IBM and Google suggest that practical, large-scale quantum computers could be developed within the next decade, potentially revolutionizing fields such as cryptography, drug discovery, and complex system modeling.",
                "output": "Quantum computing marks a revolutionary approach to computational technology, fundamentally differing from classical computing by utilizing quantum mechanics principles like superposition and entanglement. Recent advancements by tech giants suggest practical, large-scale quantum computers are potentially achievable within the next decade. This technology holds transformative potential across critical domains including cryptography, pharmaceutical research, and complex systems analysis.",
                "description": "Quantum computing overview summary"
            }
        ]
    )

    # Set an alias for the production version
    registry.add_alias(summary_v2.prompt_id, "summarizer-prod")

    print("Summarization prompts setup complete!")
    print(f"Created prompt versions: {summary_prompt.prompt_id}, {summary_v2.prompt_id}")
    print(f"Production alias 'summarizer-prod' points to: {summary_v2.prompt_id}")

if __name__ == "__main__":
    setup_summarization_prompts()