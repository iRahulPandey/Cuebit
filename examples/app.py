"""
Example Streamlit app showcasing Cuebit integration.

This app demonstrates how to use Cuebit to manage and version prompt templates
for a text summarization application.
"""

import streamlit as st
import os
from cuebit.registry import PromptRegistry

# This can be replaced with any LLM integration of your choice
# Shown here with OpenAI/LangChain for demonstration
try:
    from langchain_openai import ChatOpenAI
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Initialize Cuebit registry
registry = PromptRegistry()

# Set page configuration
st.set_page_config(
    page_title="Cuebit Text Summarization Demo",
    page_icon="📝",
    layout="wide"
)

# Main page content
st.title("📝 Text Summarization with Cuebit")
st.write("This demo shows how to use Cuebit to manage prompt templates for a summarization app.")

# Sidebar for prompt management
with st.sidebar:
    st.title("Prompt Management")
    st.write(f"Using database at: {registry.db_url}")
    
    # Initialize example prompt if needed
    if st.button("Create Example Prompt"):
        # Check if example prompt exists
        if not registry.get_prompt_by_alias("summarizer-prod"):
            prompt = registry.register_prompt(
                task="summarization",
                template="Summarize this text in a clear, concise way: {input_text}",
                meta={
                    "model": "gpt-4",
                    "temperature": 0.5,
                    "max_tokens": 300,
                    "purpose": "Generate concise summaries"
                },
                tags=["prod", "summarization"],
                project="text-summarizer",
                updated_by="streamlit_demo"
            )
            registry.add_alias(prompt.prompt_id, "summarizer-prod")
            st.success(f"Created summarization prompt with ID: {prompt.prompt_id}")
        else:
            st.info("Example prompt already exists")
    
    # List available prompts
    st.subheader("Available Prompts")
    prompts = registry.list_prompts_by_project("text-summarizer")
    if prompts:
        for p in prompts:
            alias = f" (alias: {p.alias})" if p.alias else ""
            st.write(f"v{p.version}{alias} - Updated by: {p.updated_by}")
            
            # Show prompt details in an expander
            with st.expander("Details"):
                st.code(p.template)
                st.json(p.meta)
    else:
        st.info("No prompts found. Click 'Create Example Prompt' to create one.")

# Text input area
st.subheader("Input Text")
text_input = st.text_area("Text to summarize:", height=200)

# Model selection
prompt_options = [(p.prompt_id, f"v{p.version}" + (f" ({p.alias})" if p.alias else "")) 
                  for p in prompts] if prompts else []
prompt_aliases = {p.alias: p.prompt_id for p in prompts if p.alias} if prompts else {}

prompt_selector = st.selectbox(
    "Select Prompt Template:", 
    options=["summarizer-prod"] + [id for id, _ in prompt_options],
    format_func=lambda x: x if x not in prompt_aliases else f"{x} → v{registry.get_prompt(prompt_aliases[x]).version}"
)

# LLM integration (optional)
use_mock = not LANGCHAIN_AVAILABLE
if not LANGCHAIN_AVAILABLE:
    st.warning("LangChain not installed. Using mock implementation.")
    
    # API key input if needed
    openai_api_key = st.text_input("OpenAI API Key (optional):", type="password")
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
        use_mock = False
        try:
            from langchain_openai import ChatOpenAI
            from langchain.prompts import PromptTemplate
            from langchain.chains import LLMChain
            LANGCHAIN_AVAILABLE = True
            use_mock = False
        except ImportError:
            use_mock = True

# Add a button to trigger summarization
if st.button("Summarize"):
    if text_input.strip():
        with st.spinner("Generating summary..."):
            try:
                # Get our current production prompt by alias or ID
                if prompt_selector in prompt_aliases:
                    # This is an alias
                    prompt_id = prompt_aliases[prompt_selector]
                    prompt = registry.get_prompt(prompt_id)
                else:
                    # This is a direct ID or alias
                    prompt = registry.get_prompt_by_alias(prompt_selector) or registry.get_prompt(prompt_selector)
                
                if not prompt:
                    st.error("Selected prompt not found!")
                else:
                    # Display which prompt is being used
                    st.caption(f"Using prompt version: v{prompt.version} (ID: {prompt.prompt_id[:8]}...)")
                    
                    if use_mock:
                        # Mock implementation for demo without API key
                        st.subheader("Summary:")
                        st.info("This is a mock summary. To get real summaries, install langchain and langchain_openai packages and provide an OpenAI API key.")
                        st.write(f"Would use prompt template: {prompt.template.replace('{input_text}', '[YOUR TEXT]')}")
                    else:
                        # Using LangChain for real implementation                        
                        # Create LangChain PromptTemplate
                        prompt_template = PromptTemplate(
                            input_variables=["input_text"],
                            template=prompt.template
                        )
                        
                        # Initialize LangChain ChatOpenAI model
                        llm = ChatOpenAI(
                            model=prompt.meta.get("model", "gpt-3.5-turbo"),
                            temperature=prompt.meta.get("temperature", 0.7),
                            max_tokens=prompt.meta.get("max_tokens", 500)
                        )
                        
                        # Create LLM Chain
                        summarization_chain = LLMChain(
                            llm=llm,
                            prompt=prompt_template
                        )
                        
                        # Generate summary
                        summary = summarization_chain.run(input_text=text_input)
                        
                        # Display summary
                        st.subheader("Summary:")
                        st.write(summary)
            
            except Exception as e:
                st.error(f"Error generating summary: {str(e)}")
    else:
        st.warning("Please enter some text to summarize.")

# Add a section for creating a new version of a prompt
with st.expander("Create New Prompt Version"):
    if prompts:
        # Select a prompt to base the new version on
        base_prompt_id = st.selectbox(
            "Base prompt:",
            options=[p.prompt_id for p in prompts],
            format_func=lambda x: f"v{registry.get_prompt(x).version}" + 
                                 (f" ({registry.get_prompt(x).alias})" if registry.get_prompt(x).alias else "")
        )
        
        base_prompt = registry.get_prompt(base_prompt_id)
        if base_prompt:
            # Form for editing the prompt
            new_template = st.text_area("New template:", value=base_prompt.template, height=150)
            new_temperature = st.slider("Temperature:", min_value=0.0, max_value=1.0, value=base_prompt.meta.get("temperature", 0.7), step=0.1)
            new_max_tokens = st.number_input("Max tokens:", value=base_prompt.meta.get("max_tokens", 300), min_value=1, step=50)
            updated_by = st.text_input("Your name:", value="streamlit_user")
            
            if st.button("Create New Version"):
                # Update meta with new values
                new_meta = base_prompt.meta.copy() if base_prompt.meta else {}
                new_meta["temperature"] = new_temperature
                new_meta["max_tokens"] = new_max_tokens
                
                # Create new version
                new_prompt = registry.update_prompt(
                    prompt_id=base_prompt_id,
                    new_template=new_template,
                    meta=new_meta,
                    updated_by=updated_by
                )
                
                if new_prompt:
                    st.success(f"Created new version v{new_prompt.version} with ID: {new_prompt.prompt_id}")
                    # Option to set as production
                    if st.button("Set as Production"):
                        registry.add_alias(new_prompt.prompt_id, "summarizer-prod")
                        st.success(f"Set v{new_prompt.version} as 'summarizer-prod'")
                    st.rerun()  # Refresh the page to show the new version
    else:
        st.info("Create an example prompt first before creating new versions.")

# Footer
st.markdown("---")
st.caption("Powered by Cuebit - Prompt Versioning and Management")