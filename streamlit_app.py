import streamlit as st
import requests
import json
import time
import os

# Page config
st.set_page_config(
    page_title="AI Agent Assistant",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Autonomous AI Agent")
st.markdown("Enter a request and let the AI agent plan, execute, and generate a document")

# Sidebar
with st.sidebar:
    st.header("Configuration")
    api_url = st.text_input("API URL", value="http://localhost:8000")
    st.markdown("---")
    st.markdown("### How it works")
    st.markdown("""
    1. **Planning**: Agent breaks down your request into tasks
    2. **Execution**: Each task is completed step by step
    3. **Summarization**: Results are combined
    4. **Document**: Professional Word document generated
    """)

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    request = st.text_area(
        "What would you like the AI agent to do?",
        placeholder="Example: Create a business proposal for a new software product...",
        height=150
    )
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        process_btn = st.button("🚀 Process Request", type="primary", use_container_width=True)
    with col_btn2:
        clear_btn = st.button("🗑️ Clear", use_container_width=True)

# Session state for results
if 'results' not in st.session_state:
    st.session_state.results = None

if process_btn and request:
    with st.spinner("🤔 Agent is planning and executing tasks..."):
        try:
            # Call API
            response = requests.post(
                f"{api_url}/agent",
                json={"request": request},
                timeout=300
            )
            
            if response.status_code == 200:
                st.session_state.results = response.json()
                st.success("✅ Document generated successfully!")
            else:
                st.error(f"Error: {response.text}")
                
        except requests.exceptions.RequestException as e:
            st.error(f"Connection error: {e}")
            st.info("Make sure the FastAPI server is running on port 8000")

if clear_btn:
    st.session_state.results = None
    st.rerun()

# Display results
if st.session_state.results:
    results = st.session_state.results
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📝 Tasks", "📄 Document", "📋 Raw Data"])
    
    with tab1:
        st.markdown("### Execution Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Status", results["status"])
        with col2:
            st.metric("Tasks", len(results["tasks"]))
        with col3:
            st.metric("Execution Time", f"{results['execution_time']:.2f}s")
        
        # Download button
        if results["document_path"]:
            filename = os.path.basename(results["document_path"])
            download_url = f"{api_url}/download/{filename}"
            
            st.download_button(
                label="📥 Download Word Document",
                data=requests.get(download_url).content,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
    
    with tab2:
        st.markdown("### Task Execution")
        for i, task in enumerate(results["tasks"], 1):
            with st.expander(f"Task {i}: {task[:100]}..."):
                result_key = f"task_{i-1}"
                if result_key in results["results"]:
                    st.write(results["results"][result_key])
    
    with tab3:
        st.markdown("### Generated Document Preview")
        st.text_area("Document Content", results["final_output"], height=400)
    
    with tab4:
        st.json(results)

# Footer
st.markdown("---")
st.caption("Built with FastAPI, LangGraph, and Streamlit")