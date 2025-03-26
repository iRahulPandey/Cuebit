import streamlit as st
import os
import json
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from cuebit.registry import PromptRegistry

# Set up your OpenAI API key
from dotenv import load_dotenv
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv('OPENAI_API_KEY')

# Initialize Cuebit registry
registry = PromptRegistry()

# Set page configuration
st.set_page_config(page_title="Text Summarization Chatbot", layout="wide")

# Custom CSS for better readability
st.markdown("""
<style>
.prompt-details {
    background-color: #f0f2f6;
    border-radius: 5px;
    padding: 15px;
    margin-bottom: 15px;
}
.prompt-template {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 10px;
    font-family: monospace;
    white-space: pre-wrap;
}
</style>
""", unsafe_allow_html=True)

# Title and description
st.title("📝 Intelligent Text Summarization Chatbot")
st.write("Powered by OpenAI and Cuebit Prompt Management")

# Sidebar for prompt details
st.sidebar.title("🧠 Prompt Details")

# Main content area
col1, col2 = st.columns([3, 1])

with col1:
    # Text input area
    text_input = st.text_area("Text to summarize:", height=200)

# Add a button to trigger summarization
if st.button("Generate Summary"):
    if text_input.strip():
        with st.spinner("Generating summary..."):
            try:
                # Get our current production prompt by alias
                prompt = registry.get_prompt_by_alias("summarizer-prod")
                
                if not prompt:
                    st.error("Summarization prompt not found! Run prompt_setup.py first.")
                else:
                    # Sidebar - Prompt Details
                    st.sidebar.subheader("Current Prompt Metadata")
                    
                    # Prompt Basic Info
                    st.sidebar.markdown(f"""
                    <div class="prompt-details">
                    **Prompt ID:** `{prompt.prompt_id}`
                    
                    **Version:** v{prompt.version}
                    
                    **Project:** {prompt.project or 'Unassigned'}
                    
                    **Updated By:** {prompt.updated_by or 'Unknown'}
                    
                    **Updated At:** {prompt.updated_at.strftime('%Y-%m-%d %H:%M')}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Prompt Template
                    st.sidebar.subheader("Prompt Template")
                    st.sidebar.markdown(f'<div class="prompt-template">{prompt.template}</div>', unsafe_allow_html=True)
                    
                    # Metadata
                    st.sidebar.subheader("Model Configuration")
                    metadata_str = json.dumps(prompt.meta, indent=2)
                    st.sidebar.code(metadata_str)
                    
                    # Tags
                    tags = json.loads(prompt.tags or "[]")
                    if tags:
                        st.sidebar.subheader("Tags")
                        tag_html = " ".join([f'<span class="badge bg-primary text-light me-1">{tag}</span>' for tag in tags])
                        st.sidebar.markdown(tag_html, unsafe_allow_html=True)
                    
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
                    st.subheader("🔍 Generated Summary")
                    st.write(summary)
                    
                    # Show prompt version and other details
                    st.markdown(f"""
                    ### Prompt Details
                    - **Version:** v{prompt.version}
                    - **Prompt ID:** `{prompt.prompt_id}`
                    - **Model:** {prompt.meta.get('model', 'N/A')}
                    - **Temperature:** {prompt.meta.get('temperature', 'N/A')}
                    """)
                    
                    # Show examples if available
                    examples = registry.get_examples(prompt.prompt_id)
                    if examples:
                        with st.expander("📚 Prompt Examples"):
                            for i, ex in enumerate(examples, 1):
                                st.markdown(f"**Example {i}:**")
                                st.markdown(f"**Input:** {ex.get('input', 'N/A')}")
                                st.markdown(f"**Output:** {ex.get('output', 'N/A')}")
                                if ex.get('description'):
                                    st.caption(f"Description: {ex['description']}")
            
            except Exception as e:
                st.error(f"Error generating summary: {str(e)}")
    else:
        st.warning("Please enter some text to summarize.")

# List available prompt versions at the bottom
st.markdown("---")
st.subheader("📋 Available Prompt Versions")

# List available summarization prompts
prompts = registry.list_prompts_by_project("text-summarizer")
if prompts:
    # Create a table of prompts
    prompt_data = []
    for p in prompts:
        prompt_data.append({
            "Version": f"v{p.version}",
            "Alias": p.alias or "—",
            "Updated By": p.updated_by or "Unknown",
            "Updated At": p.updated_at.strftime('%Y-%m-%d %H:%M'),
            "Prompt ID": p.prompt_id
        })
    
    # Display as a table
    st.table(prompt_data)
else:
    st.info("No prompts found. Run prompt_setup.py first.")

# Footer
st.markdown("""
---
**Powered by:**
- OpenAI's Language Models
- LangChain
- CueBit Prompt Registry
""")