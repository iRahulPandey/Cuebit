"""
Streamlit dashboard for Cuebit prompt management.

This dashboard provides a visual interface for managing and exploring
prompts in the Cuebit registry, with features for editing, comparing,
and visualizing prompt versions.
"""

import streamlit as st
import json
import re
import difflib
from collections import Counter
from datetime import datetime, timedelta
import pandas as pd
import altair as alt
import os
import tempfile

from cuebit.registry import PromptRegistry

# Set page config
st.set_page_config(
    page_title="Cuebit Prompt Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize registry
registry = PromptRegistry()

# Print DB URL during startup to help with troubleshooting
print(f"Using database at: {registry.db_url}")

# Add custom CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    .prompt-box {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .tag {
        background-color: #f1f1f1;
        border-radius: 3px;
        padding: 2px 5px;
        margin-right: 5px;
        font-size: 0.8em;
    }
    .version-tag {
        background-color: #6c757d;
        color: white;
        border-radius: 3px;
        padding: 2px 5px;
        font-size: 0.8em;
    }
    .alias-tag {
        background-color: #28a745;
        color: white;
        border-radius: 3px;
        padding: 2px 5px;
        font-size: 0.8em;
    }
    .diff-add {
        background-color: #e6ffec;
        color: #24292f;
    }
    .diff-remove {
        background-color: #ffebe9;
        color: #24292f;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation ---
st.sidebar.title("🧠 Cuebit")
st.sidebar.caption("Prompt Management System")

# Navigation options
nav_options = [
    "📊 Dashboard", 
    "🗂️ Prompt Explorer", 
    "🔨 Prompt Builder", 
    "📈 Version History", 
    "🔄 Import/Export"
]

# Database location
st.sidebar.caption(f"DB: {registry.db_url}")

nav_selection = st.sidebar.radio("Navigation", nav_options)

# --- Helper Functions ---
def format_tags(tags_str):
    """Format tags string into HTML tags."""
    try:
        tags = json.loads(tags_str or "[]")
        return " ".join([f'<span class="tag">{tag}</span>' for tag in tags])
    except:
        return ""

def render_version_history(project, task):
    """Render version history for a project/task."""
    history = registry.get_version_history(project, task)
    
    if not history:
        st.info(f"No history found for {project}/{task}")
        return
    
    # Create a table of versions
    data = []
    for p in history:
        # Handle both ORM objects and dictionaries
        if isinstance(p, dict):
            # Dictionary access
            data.append({
                "prompt_id": p.get("prompt_id", ""),
                "version": p.get("version", 0),
                "updated_by": p.get("updated_by") or "Unknown",
                "updated_at": p.get("updated_at", datetime.now()),
                "alias": p.get("alias", ""),
                "has_alias": bool(p.get("alias", ""))
            })
        else:
            # ORM object access
            data.append({
                "prompt_id": p.prompt_id,
                "version": p.version,
                "updated_by": p.updated_by or "Unknown",
                "updated_at": p.updated_at,
                "alias": p.alias or "",
                "has_alias": bool(p.alias)
            })
    
    df = pd.DataFrame(data)
    if df.empty:
        st.info(f"No version history found for {project}/{task}")
        return
        
    df = df.sort_values("version", ascending=False)
    
    # Show the version history
    st.subheader(f"Version History: {project}/{task}")
    
    # Use AgGrid or custom formatting for the table
    col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])
    col1.markdown("**Version**")
    col2.markdown("**Updated By**")
    col3.markdown("**Updated At**")
    col4.markdown("**Alias**")
    col5.markdown("**Actions**")
    
    selected_versions = []
    
    for idx, row in df.iterrows():
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])
            col1.markdown(f"v{row['version']}")
            col2.markdown(row["updated_by"])
            
            # Handle different date formats
            if isinstance(row["updated_at"], datetime):
                updated_at_str = row["updated_at"].strftime("%Y-%m-%d %H:%M")
            elif isinstance(row["updated_at"], str):
                try:
                    # Try to parse the date string
                    updated_at = datetime.fromisoformat(row["updated_at"].replace('Z', '+00:00'))
                    updated_at_str = updated_at.strftime("%Y-%m-%d %H:%M")
                except:
                    # If parsing fails, just use the string
                    updated_at_str = row["updated_at"]
            else:
                updated_at_str = str(row["updated_at"])
                
            col3.markdown(updated_at_str)
            
            if row["has_alias"]:
                col4.markdown(f'<span class="alias-tag">{row["alias"]}</span>', unsafe_allow_html=True)
            else:
                col4.markdown("—")
                
            # Add to comparison selection
            is_selected = col5.checkbox("Select", key=f"select_{row['prompt_id']}")
            if is_selected:
                selected_versions.append(row["prompt_id"])
    
    # Compare versions if exactly 2 are selected
    if len(selected_versions) == 2:
        st.subheader("Compare Selected Versions")
        
        # Get comparison
        comparison = registry.compare_versions(selected_versions[0], selected_versions[1])
        
        # Show template diff
        st.markdown("### Template Differences")
        diff_html = ""
        for line in comparison["template_diff"]:
            if line.startswith("+"):
                diff_html += f'<div class="diff-add">{line}</div>'
            elif line.startswith("-"):
                diff_html += f'<div class="diff-remove">{line}</div>'
            else:
                diff_html += f'<div>{line}</div>'
        
        st.markdown(diff_html, unsafe_allow_html=True)
        
        # Show metadata changes
        st.markdown("### Metadata Changes")
        
        if comparison["meta_changes"]["added"]:
            st.markdown("**Added:**")
            st.json(comparison["meta_changes"]["added"])
            
        if comparison["meta_changes"]["removed"]:
            st.markdown("**Removed:**")
            st.json(comparison["meta_changes"]["removed"])
            
        if comparison["meta_changes"]["changed"]:
            st.markdown("**Changed:**")
            st.json(comparison["meta_changes"]["changed"])
            
        # Show tag changes
        st.markdown("### Tag Changes")
        
        if comparison["tags_changes"]["added"]:
            st.markdown(f"**Added:** {', '.join(comparison['tags_changes']['added'])}")
            
        if comparison["tags_changes"]["removed"]:
            st.markdown(f"**Removed:** {', '.join(comparison['tags_changes']['removed'])}")
            
        # Show variable changes
        st.markdown("### Variable Changes")
        
        if comparison["variables_changes"]["added"]:
            st.markdown(f"**Added:** {', '.join(comparison['variables_changes']['added'])}")
            
        if comparison["variables_changes"]["removed"]:
            st.markdown(f"**Removed:** {', '.join(comparison['variables_changes']['removed'])}")
            
    elif len(selected_versions) > 2:
        st.warning("Please select exactly 2 versions to compare")

def render_prompt_detail(prompt_id):
    """Render detailed view of a prompt."""
    prompt = registry.get_prompt(prompt_id)
    if not prompt:
        st.error("Prompt not found")
        return
    
    # Add a back button at the top
    if st.button("← Back to Prompt Explorer", key="back_button_top"):
        st.session_state.pop("selected_prompt", None)
        st.rerun()
    
    # Get lineage information
    lineage = registry.get_prompt_lineage(prompt_id)
    
    # Display prompt basic info
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"### {prompt.task} (v{prompt.version})")
        if prompt.alias:
            st.markdown(f'<span class="alias-tag">Alias: {prompt.alias}</span>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"**Project:** {prompt.project or 'Unassigned'}")
        st.markdown(f"**Updated by:** {prompt.updated_by or 'Unknown'}")
        st.markdown(f"**Updated at:** {prompt.updated_at.strftime('%Y-%m-%d %H:%M')}")
    
    # Display template
    st.markdown("### Template")
    st.code(prompt.template)
    
    # Display template variables
    if prompt.template_variables:
        st.markdown("### Template Variables")
        for var in prompt.template_variables:
            st.markdown(f"- `{{{var}}}`")
    
    # Display metadata
    st.markdown("### Metadata")
    st.json(prompt.meta)
    
    # Display tags
    if prompt.tags:
        st.markdown("### Tags")
        tags = json.loads(prompt.tags or "[]")
        for tag in tags:
            st.markdown(f'<span class="tag">{tag}</span>', unsafe_allow_html=True)
    
    # Display version history
    st.markdown("### Version History")
    
    # Show ancestors
    if lineage["ancestors"]:
        st.markdown("**Previous versions:**")
        for ancestor in lineage["ancestors"]:
            st.markdown(f"- v{ancestor.version} by {ancestor.updated_by or 'Unknown'} on {ancestor.updated_at.strftime('%Y-%m-%d')}")
    
    # Show descendants
    if lineage["descendants"]:
        st.markdown("**Later versions:**")
        for descendant in lineage["descendants"]:
            st.markdown(f"- v{descendant.version} by {descendant.updated_by or 'Unknown'} on {descendant.updated_at.strftime('%Y-%m-%d')}")
    
    # Get examples
    examples = registry.get_examples(prompt_id)
    if examples:
        st.markdown("### Examples")
        for ex in examples:
            with st.expander(f"Example: {ex['description'] or 'Unnamed example'}"):
                st.markdown("**Input:**")
                st.text(ex["input"])
                st.markdown("**Output:**")
                st.text(ex["output"])
    
    # Actions
    st.markdown("### Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Edit", key=f"edit_{prompt_id}"):
            st.session_state["edit_prompt"] = prompt_id
            st.session_state.pop("selected_prompt", None)
            st.rerun()
            
    with col2:
        if st.button("Set Alias", key=f"alias_{prompt_id}"):
            st.session_state["alias_prompt"] = prompt_id
            st.session_state.pop("selected_prompt", None)
            st.rerun()
            
    with col3:
        if st.button("Copy ID", key=f"copy_{prompt_id}"):
            st.code(prompt_id)
            
    with col4:
        if st.button("Delete", key=f"delete_{prompt_id}"):
            if registry.soft_delete_prompt(prompt_id):
                st.success("Prompt deleted successfully")
                st.session_state.pop("selected_prompt", None)
                st.rerun()
    
    # Add another back button at the bottom for better UX
    if st.button("← Back to Prompt Explorer", key="back_button_bottom"):
        st.session_state.pop("selected_prompt", None)
        st.rerun()

def prompt_builder():
    """Prompt builder component."""
    st.header("🔨 Prompt Builder")
    
    # Initialize session state for form
    if "builder_form" not in st.session_state:
        st.session_state.builder_form = {
            "project": "",
            "task": "",
            "template": "",
            "tags": "",
            "meta": "{\n  \"model\": \"gpt-4\",\n  \"temperature\": 0.7\n}",
            "updated_by": "",
            "examples": []
        }
    
    # Check if we're editing an existing prompt
    editing = "edit_prompt" in st.session_state
    
    if editing:
        prompt = registry.get_prompt(st.session_state["edit_prompt"])
        if prompt:
            # Pre-populate form with prompt data
            st.session_state.builder_form = {
                "project": prompt.project or "",
                "task": prompt.task,
                "template": prompt.template,
                "tags": ", ".join(json.loads(prompt.tags or "[]")),
                "meta": json.dumps(prompt.meta, indent=2) if prompt.meta else "{}",
                "updated_by": prompt.updated_by or "",
                "examples": registry.get_examples(prompt.prompt_id)
            }
            
            st.subheader(f"Editing: {prompt.task} (v{prompt.version})")
        else:
            st.error("Prompt not found")
            st.session_state.pop("edit_prompt", None)
            return
    else:
        st.subheader("Create New Prompt")
    
    # Project selection or creation
    projects = registry.list_projects()
    project_options = [""] + projects + ["+ Create New Project"]
    selected_project = st.selectbox(
        "Select Project", 
        project_options,
        index=project_options.index(st.session_state.builder_form["project"]) if st.session_state.builder_form["project"] in project_options else 0
    )
    
    if selected_project == "+ Create New Project":
        selected_project = st.text_input("New Project Name")
    
    # Task selection
    task = st.text_input("Task", value=st.session_state.builder_form["task"])
    
    # Template builder
    st.subheader("Template Editor")
    template = st.text_area(
        "Prompt Template", 
        value=st.session_state.builder_form["template"],
        height=200, 
        help="Use {variable_name} syntax for variables"
    )
    
    # Extract variables from template
    variables = []
    if template:
        variables = re.findall(r'\{([^{}]*)\}', template)
        if variables:
            st.markdown("**Detected Variables:**")
            for var in variables:
                st.markdown(f"- `{{{var}}}`")
    
    # Template validation
    if template:
        validation = registry.validate_template(template)
        if not validation["is_valid"]:
            st.error("Template validation failed")
            for warning in validation["warnings"]:
                st.warning(warning)
    
    # Tags
    tags = st.text_input(
        "Tags (comma separated)", 
        value=st.session_state.builder_form["tags"],
        help="Example: prod, summarization, gpt-4"
    )
    
    # Metadata
    meta_str = st.text_area(
        "Metadata (JSON)", 
        value=st.session_state.builder_form["meta"],
        height=150,
        help="JSON metadata including model information"
    )
    
    try:
        meta = json.loads(meta_str)
    except json.JSONDecodeError:
        st.error("Invalid JSON in metadata")
        meta = {}
    
    # User attribution
    updated_by = st.text_input(
        "Updated by (username)", 
        value=st.session_state.builder_form["updated_by"]
    )
    
    # Examples
    st.subheader("Examples")
    
    # Show existing examples
    for i, example in enumerate(st.session_state.builder_form["examples"]):
        with st.expander(f"Example {i+1}: {example.get('description', 'Unnamed')}"):
            st.text_input("Description", value=example.get("description", ""), key=f"ex_desc_{i}")
            st.text_area("Input", value=example.get("input", ""), key=f"ex_input_{i}")
            st.text_area("Output", value=example.get("output", ""), key=f"ex_output_{i}")
            
            if st.button("Remove Example", key=f"remove_ex_{i}"):
                st.session_state.builder_form["examples"].pop(i)
                st.rerun()
    
    # Add new example
    with st.expander("Add Example"):
        ex_description = st.text_input("Description", key="new_ex_desc")
        ex_input = st.text_area("Input", key="new_ex_input")
        ex_output = st.text_area("Output", key="new_ex_output")
        
        if st.button("Add Example"):
            st.session_state.builder_form["examples"].append({
                "description": ex_description,
                "input": ex_input,
                "output": ex_output
            })
            st.rerun()
    
    # Preview rendered prompt
    if variables and template:
        st.subheader("Preview")
        preview_expander = st.expander("Render with example variables")
        
        with preview_expander:
            preview_vars = {}
            for var in variables:
                preview_vars[var] = st.text_input(f"Value for {{{var}}}", key=f"preview_{var}")
            
            if st.button("Preview"):
                rendered = template
                for var, value in preview_vars.items():
                    rendered = rendered.replace(f"{{{var}}}", value)
                
                st.markdown("**Rendered Prompt:**")
                st.markdown("---")
                st.markdown(rendered)
                st.markdown("---")
    
    # Action buttons - add a Cancel button for better UX
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Save Prompt"):
            try:
                # Process tags
                tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
                
                # Process examples
                examples_list = []
                for ex in st.session_state.builder_form["examples"]:
                    examples_list.append({
                        "input": ex.get("input", ""),
                        "output": ex.get("output", ""),
                        "description": ex.get("description", "")
                    })
                
                if editing:
                    # Update existing prompt
                    updated_prompt = registry.update_prompt(
                        st.session_state["edit_prompt"],
                        template,
                        meta,
                        updated_by,
                        tag_list,
                        examples_list
                    )
                    if updated_prompt:
                        st.success(f"Prompt updated successfully! New version: v{updated_prompt.version}")
                        st.session_state.pop("edit_prompt", None)
                        # Clear the form
                        st.session_state.builder_form = {
                            "project": "",
                            "task": "",
                            "template": "",
                            "tags": "",
                            "meta": "{\n  \"model\": \"gpt-4\",\n  \"temperature\": 0.7\n}",
                            "updated_by": "",
                            "examples": []
                        }
                    else:
                        st.error("Error updating prompt")
                else:
                    # Register new prompt
                    new_prompt = registry.register_prompt(
                        task=task,
                        template=template,
                        meta=meta,
                        tags=tag_list,
                        project=selected_project,
                        updated_by=updated_by,
                        examples=examples_list
                    )
                    
                    st.success(f"Prompt saved successfully! ID: {new_prompt.prompt_id}")
                    
                    # Clear the form
                    st.session_state.builder_form = {
                        "project": "",
                        "task": "",
                        "template": "",
                        "tags": "",
                        "meta": "{\n  \"model\": \"gpt-4\",\n  \"temperature\": 0.7\n}",
                        "updated_by": "",
                        "examples": []
                    }
                    
                    # Add alias if requested
                    st.session_state["alias_prompt"] = new_prompt.prompt_id
                    
            except Exception as e:
                st.error(f"Error saving prompt: {str(e)}")
    
    with col2:
        # Cancel button to return to previous view
        if st.button("Cancel"):
            if editing:
                st.session_state.pop("edit_prompt", None)
            # Clear the form
            st.session_state.builder_form = {
                "project": "",
                "task": "",
                "template": "",
                "tags": "",
                "meta": "{\n  \"model\": \"gpt-4\",\n  \"temperature\": 0.7\n}",
                "updated_by": "",
                "examples": []
            }
            st.rerun()

def set_alias_form():
    """Form for setting an alias on a prompt."""
    if "alias_prompt" not in st.session_state:
        return
        
    prompt = registry.get_prompt(st.session_state["alias_prompt"])
    if not prompt:
        st.error("Prompt not found")
        st.session_state.pop("alias_prompt", None)
        return
        
    st.subheader(f"Set Alias for: {prompt.task} (v{prompt.version})")
    
    alias = st.text_input("Alias", value=prompt.alias or "")
    overwrite = st.checkbox("Overwrite existing alias", value=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Set Alias"):
            if not alias:
                st.error("Alias cannot be empty")
            else:
                updated = registry.add_alias(prompt.prompt_id, alias, overwrite)
                if updated:
                    st.success(f"Alias '{alias}' set for prompt v{prompt.version}")
                    st.session_state.pop("alias_prompt", None)
                    st.rerun()
                else:
                    st.error("Failed to set alias")
    
    with col2:
        if st.button("Cancel"):
            st.session_state.pop("alias_prompt", None)
            st.rerun()

def prompt_explorer():
    """Prompt explorer component."""
    st.header("🗂️ Prompt Explorer")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Project filter
        projects = registry.list_projects()
        selected_project = st.selectbox("Filter by Project", ["All Projects"] + projects)
    
    with col2:
        # Tag filter
        all_tags = registry.get_tag_stats().most_common()
        tag_options = [tag for tag, _ in all_tags]
        selected_tag = st.multiselect("Filter by Tag", tag_options)
    
    with col3:
        # Search
        search_term = st.text_input("Search", placeholder="Search prompts...")
    
    # Get filtered prompts
    if selected_project != "All Projects":
        prompts = registry.list_prompts_by_project(selected_project)
    else:
        prompts, _ = registry.list_prompts()
    
    # Apply tag filter
    if selected_tag:
        filtered_prompts = []
        for p in prompts:
            try:
                tags = json.loads(p.tags or "[]")
                if any(tag in tags for tag in selected_tag):
                    filtered_prompts.append(p)
            except:
                pass
        prompts = filtered_prompts
    
    # Apply search filter
    if search_term:
        filtered_prompts = []
        for p in prompts:
            if (search_term.lower() in p.template.lower() or
                search_term.lower() in p.task.lower() or
                (p.project and search_term.lower() in p.project.lower())):
                filtered_prompts.append(p)
        prompts = filtered_prompts
    
    # Group by project/task
    from collections import defaultdict
    projects_map = defaultdict(lambda: defaultdict(list))
    
    for p in prompts:
        project = p.project or "Unassigned"
        projects_map[project][p.task].append(p)
    
    # Display prompts
    if not projects_map:
        st.info("No prompts found with the current filters")
    else:
        for project_name in sorted(projects_map.keys()):
            with st.expander(f"📁 {project_name}", expanded=True):
                for task_name in sorted(projects_map[project_name].keys()):
                    st.markdown(f"**{task_name}**")
                    
                    # Sort by version
                    versions = sorted(projects_map[project_name][task_name], key=lambda x: x.version, reverse=True)
                    
                    for p in versions:
                        # Create card-like prompt display
                        col1, col2, col3, col4 = st.columns([3, 2, 3, 2])
                        
                        with col1:
                            version_text = f'<span class="version-tag">v{p.version}</span>'
                            if p.alias:
                                version_text += f' <span class="alias-tag">{p.alias}</span>'
                            st.markdown(version_text, unsafe_allow_html=True)
                            
                        with col2:
                            tags = json.loads(p.tags or "[]")
                            if tags:
                                tags_html = " ".join([f'<span class="tag">{tag}</span>' for tag in tags])
                                st.markdown(tags_html, unsafe_allow_html=True)
                            
                        with col3:
                            update_info = f"By: {p.updated_by or 'Unknown'}"
                            update_info += f" on {p.updated_at.strftime('%Y-%m-%d')}"
                            st.markdown(update_info)
                            
                        with col4:
                            if st.button("View", key=f"view_{p.prompt_id}"):
                                st.session_state["selected_prompt"] = p.prompt_id
                                st.rerun()
                    
                    # Add separator between tasks
                    st.markdown("---")

def dashboard_view():
    """Main dashboard view with statistics and charts."""
    st.header("📊 Dashboard")
    
    # Get registry stats
    stats = registry.get_usage_stats()
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Prompts", stats["total_prompts"])
    
    with col2:
        st.metric("Active Prompts", stats["active_prompts"])
    
    with col3:
        st.metric("Projects", stats["total_projects"])
    
    with col4:
        st.metric("Aliases", stats["prompts_with_aliases"])
    
    # Display charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top Projects")
        
        # Convert to DataFrame for charting
        project_data = [{"project": p, "count": c} for p, c in stats["most_active_projects"]]
        project_df = pd.DataFrame(project_data)
        
        if not project_df.empty:
            chart = alt.Chart(project_df).mark_bar().encode(
                x=alt.X('count:Q', title='Number of Prompts'),
                y=alt.Y('project:N', title='Project', sort='-x'),
                tooltip=['project', 'count']
            ).properties(
                title='Projects by Prompt Count'
            )
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No project data available")
    
    with col2:
        st.subheader("Top Tags")
        
        # Convert to DataFrame for charting
        tag_data = [{"tag": t, "count": c} for t, c in stats["top_tags"]]
        tag_df = pd.DataFrame(tag_data)
        
        if not tag_df.empty:
            chart = alt.Chart(tag_df).mark_bar().encode(
                x=alt.X('count:Q', title='Number of Prompts'),
                y=alt.Y('tag:N', title='Tag', sort='-x'),
                tooltip=['tag', 'count']
            ).properties(
                title='Tags by Usage'
            )
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No tag data available")
    
    # Recent prompts
    st.subheader("Recent Prompts")
    
    # Get all prompts sorted by update date
    prompts, _ = registry.list_prompts()
    recent_prompts = sorted(prompts, key=lambda p: p.updated_at, reverse=True)[:10]
    
    if recent_prompts:
        # Display as table
        data = []
        for p in recent_prompts:
            data.append({
                "ID": p.prompt_id,
                "Project": p.project or "Unassigned",
                "Task": p.task,
                "Version": p.version,
                "Alias": p.alias or "—",
                "Updated By": p.updated_by or "Unknown",
                "Updated At": p.updated_at.strftime("%Y-%m-%d %H:%M")
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df)
    else:
        st.info("No prompts available")

def version_history_view():
    """View version history for projects/tasks."""
    st.header("📈 Version History")
    
    # Project/task selection
    col1, col2 = st.columns(2)
    
    with col1:
        projects = registry.list_projects()
        selected_project = st.selectbox("Select Project", projects)
    
    if selected_project:
        with col2:
            # Get tasks for this project
            project_prompts = registry.list_prompts_by_project(selected_project)
            tasks = list(set([p.task for p in project_prompts]))
            
            selected_task = st.selectbox("Select Task", tasks)
    
    # Show version history if project/task selected
    if selected_project and selected_task:
        render_version_history(selected_project, selected_task)

def import_export_view():
    """Import/export prompts view."""
    st.header("🔄 Import/Export")
    
    # Export tab
    export_tab, import_tab = st.tabs(["Export", "Import"])
    
    with export_tab:
        st.subheader("Export Prompts")
        
        # Project selection for export
        projects = registry.list_projects()
        export_project = st.selectbox("Export from Project", ["All Projects"] + projects)
        
        # Format selection
        export_format = st.radio("Export Format", ["JSON", "YAML"])
        
        if st.button("Export"):
            try:
                project = None if export_project == "All Projects" else export_project
                exported = registry.export_prompts(
                    project=project, 
                    format=export_format.lower()
                )
                
                if exported:
                    # Create download button
                    st.download_button(
                        label="Download Export",
                        data=exported,
                        file_name=f"cuebit_export_{datetime.now().strftime('%Y%m%d')}.{export_format.lower()}",
                        mime="application/json" if export_format.lower() == "json" else "application/yaml"
                    )
                else:
                    st.error("No data to export")
            except Exception as e:
                st.error(f"Export error: {str(e)}")
    
    with import_tab:
        st.subheader("Import Prompts")
        
        # Upload file
        uploaded_file = st.file_uploader("Upload Import File", type=["json", "yaml", "yml"])
        
        skip_existing = st.checkbox("Skip Existing Prompts", value=True)
        
        if uploaded_file is not None:
            # Determine format from file extension
            file_format = uploaded_file.name.split(".")[-1].lower()
            if file_format == "yml":
                file_format = "yaml"
            
            # Read file content
            import_data = uploaded_file.read().decode("utf-8")
            
            if st.button("Import"):
                try:
                    results = registry.import_prompts(
                        data=import_data,
                        format=file_format,
                        skip_existing=skip_existing
                    )
                    
                    if "error" in results:
                        st.error(f"Import error: {results['error']}")
                    else:
                        st.success(f"""
                        Import completed:
                        - Total: {results['total']}
                        - Imported: {results['imported']}
                        - Skipped: {results['skipped']}
                        - Errors: {results['errors']}
                        """)
                except Exception as e:
                    st.error(f"Import error: {str(e)}")

# --- Main Content Based on Navigation ---
if "alias_prompt" in st.session_state:
    set_alias_form()
elif "selected_prompt" in st.session_state:
    render_prompt_detail(st.session_state["selected_prompt"])
elif nav_selection == "🔨 Prompt Builder":
    prompt_builder()
elif nav_selection == "🗂️ Prompt Explorer":
    prompt_explorer()
elif nav_selection == "📈 Version History":
    version_history_view()
elif nav_selection == "🔄 Import/Export":
    import_export_view()
else:  # Default to Dashboard
    dashboard_view()

# Show footer
st.markdown("---")
st.markdown("Cuebit Prompt Manager | v0.2.0")