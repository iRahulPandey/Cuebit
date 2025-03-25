# cuebit_dashboard.py
import streamlit as st
import json
from collections import Counter
from cuebit.registry import PromptRegistry
import altair as alt
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Cuebit Dashboard", layout="wide")

registry = PromptRegistry()
prompts = registry.list_prompts()
projects = registry.list_projects()
tag_stats = registry.get_tag_stats()

# --- 📊 Dashboard Header ---
st.title("📊 Cuebit Prompt Manager")

# --- 🧠 Stats Overview ---
total_prompts = len(prompts)
total_projects = len(set([p.project or "Unassigned" for p in prompts]))
total_tags = len(tag_stats)
prod_versions = tag_stats.get("prod", 0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Projects", total_projects)
col2.metric("Total Prompts", total_prompts)
col3.metric("Versions in Production", prod_versions)
col4.metric("Unique Tags", total_tags)

# --- 📈 Tag Distribution Chart ---
if tag_stats:
    tag_df = pd.DataFrame(tag_stats.items(), columns=["Tag", "Count"])
    chart = (
        alt.Chart(tag_df)
        .mark_bar()
        .encode(
            x=alt.X("Tag", sort="-y"),
            y="Count",
            tooltip=["Tag", "Count"]
        )
        .properties(title="Tag Distribution", width=600)
    )
    st.altair_chart(chart, use_container_width=True)

st.divider()

# --- 🗂 Project + Prompt Explorer ---
st.subheader("🗂 Prompt Explorer")
from collections import defaultdict

projects_map = defaultdict(list)
for p in prompts:
    projects_map[p.project or "Unassigned"].append(p)

for project_name in sorted(projects_map.keys()):
    with st.expander(f"📁 {project_name}", expanded=False):
        versions = sorted(projects_map[project_name], key=lambda x: x.version)

        for p in versions:
            tag_list = json.loads(p.tags or "[]")
            col1, col2, col3, col4, col5 = st.columns([3, 2, 3, 3, 2])
            with col1:
                st.markdown(f"**v{p.version}** — `{p.task}`")
            with col2:
                st.text(f"Alias: {p.alias or '—'}")
            with col3:
                st.markdown("**Tags:** " + ", ".join([f"`{tag}`" for tag in tag_list]) or "—")
            with col4:
                st.text(f"By: {p.updated_by or '—'}")
            with col5:
                if st.button("🔍 View", key=p.prompt_id):
                    st.session_state["selected_prompt"] = p.prompt_id

# --- 🧪 Selected Prompt Viewer ---
if "selected_prompt" in st.session_state:
    selected_id = st.session_state["selected_prompt"]
    prompt = registry.get_prompt(selected_id)
    if prompt:
        st.sidebar.markdown("### 🔎 Prompt Details")
        st.sidebar.text(f"Prompt ID: {prompt.prompt_id}")
        st.sidebar.text(f"Version: v{prompt.version}")
        st.sidebar.text(f"Alias: {prompt.alias or '—'}")
        st.sidebar.text(f"Project: {prompt.project or '—'}")
        st.sidebar.text(f"Task: {prompt.task}")
        st.sidebar.text(f"Updated by: {prompt.updated_by or '—'}")
        st.sidebar.text(f"Created at: {prompt.created_at.strftime('%Y-%m-%d %H:%M:%S') if prompt.created_at else '—'}")
        st.sidebar.text(f"Updated at: {prompt.updated_at.strftime('%Y-%m-%d %H:%M:%S') if prompt.updated_at else '—'}")
        st.sidebar.json(prompt.meta)

        st.subheader(f"📝 Template: v{prompt.version}")
        st.code(prompt.template, language="jinja2")

        with st.expander("🧪 Test this prompt"):
            user_input = st.text_area("Input for `{input}`", height=100)
            if st.button("▶️ Render Prompt"):
                rendered = prompt.template.replace("{input}", user_input)
                st.code(rendered, language="markdown")