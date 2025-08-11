import streamlit as st
import requests
import json


API_URL = "http://localhost:8082"


st.set_page_config(page_title="Research Assistant", layout="wide")
st.title("Research Assistant")


if 'step' not in st.session_state:
    st.session_state.step = 0
    
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False


def init_plan_state(plan):
    st.session_state.plan = plan
    st.session_state.topic = plan.get("topic", "")
    st.session_state.internal_sources = plan.get("internal_sources", [])
    st.session_state.external_sources = plan.get("external_sources", [])
    st.session_state.steps = plan.get("steps", [])


def render_plan_display():
    """Display the plan in a readable format"""
    st.subheader("Research Plan")
    
    st.markdown(f"**Topic:** {st.session_state.topic}")
    
    # Show plan overview if available
    plan_text = getattr(st.session_state, 'plan', {}).get('plan_text', '')
    if plan_text:
        st.markdown(f"**Plan Overview:** {plan_text}")
    
    st.markdown("**Research Steps:**")
    for i, step in enumerate(st.session_state.steps, 1):
        st.markdown(f"{i}. {step.get('query', '')}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Internal Sources:**")
        ints = st.session_state.internal_sources or []
        if ints:
            for s in ints:
                title = s.get('title', 'Unknown Document')
                doc_type = s.get('type', 'document')
                st.write(f"• **{title}** ({doc_type})")
                
                # Show preview if available
                preview = s.get('preview', '')
                if preview and preview.strip():
                    st.caption(f"Preview: {preview}")
                
                # Show relevance score if available
                score = s.get('relevance_score')
                if score is not None:
                    st.caption(f"Relevance: {score:.2f}")
        else:
            st.write("• No relevant internal documents found for this topic")
            st.caption("The system searched internal documents but found no relevant matches")
    
    with col2:
        st.markdown("**External Sources Found:**")
        exts = st.session_state.external_sources or []
        if exts:
            for s in exts:
                name = s.get('name', 'Unknown Source')
                title = s.get('title', '')
                st.write(f"• **{name}**")
                
                if title:
                    st.caption(f"Title: {title}")
                
                # Show preview if available
                preview = s.get('preview', '')
                if preview and preview.strip():
                    st.caption(f"Preview: {preview}")
        else:
            st.write("• No external sources discovered yet")
            st.caption("External sources will be searched during research execution")


def render_plan_editor():
    st.subheader("Edit Research Plan")
    
    # Show topic as readonly
    st.text_input("Research Topic:", value=st.session_state.topic, disabled=True, help="Topic cannot be edited")
    
    st.markdown("**Research Steps:**")
    
    # Add step button
    if st.button("Add Step"):
        st.session_state.steps.append({"query": ""})
        st.rerun()
    
    # Editable step list
    for i, step in enumerate(st.session_state.steps):
        col_query, col_remove = st.columns([8, 1])
        
        # Editable query text
        step["query"] = col_query.text_input(
            label=f"Step {i+1}",
            value=step.get("query", ""),
            key=f"step_{i}"
        )
        
        # Remove button
        if col_remove.button("X", key=f"rm_{i}", help="Remove this step"):
            st.session_state.steps.pop(i)
            st.rerun()
    
    st.markdown("---")
    
    # Show sources as readonly
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Internal Sources** (Auto-detected)")
        for s in st.session_state.internal_sources:
            st.write(f"• {s.get('title', '')}")
    
    with col2:
        st.markdown("**External Sources** (Auto-detected)")
        if st.session_state.external_sources:
            for s in st.session_state.external_sources:
                st.write(f"• {s.get('name', '')}")
        else:
            st.write("• Will be discovered during research")


def render_plan_review():
    col1, col2, col3 = st.columns([2, 2, 3])
    
    with col1:
        if st.button("Edit Plan" if not st.session_state.edit_mode else "View Plan"):
            st.session_state.edit_mode = not st.session_state.edit_mode
            st.rerun()
    
    with col2:
        if st.session_state.edit_mode and st.button("Save Changes", type="primary"):
            st.session_state.edit_mode = False
            st.success("Changes saved!")
            st.rerun()
    
    with col3:
        if st.button("Start Research", type="primary", disabled=st.session_state.edit_mode):
            if st.session_state.edit_mode:
                st.warning("Please save your changes before proceeding.")
            else:
                execute_research_plan()
    
    st.markdown("---")
    
    if st.session_state.edit_mode:
        render_plan_editor()
    else:
        render_plan_display()


def execute_research_plan():
    try:
        if not st.session_state.topic.strip():
            st.error("Please provide a research topic.")
            st.stop()
        
        if not st.session_state.steps:
            st.error("Please add at least one research step.")
            st.stop()
        
        empty_queries = [i+1 for i, step in enumerate(st.session_state.steps) if not step.get("query", "").strip()]
        if empty_queries:
            st.error(f"Please provide queries for step(s): {', '.join(map(str, empty_queries))}")
            st.stop()
        
        plan_to_send = {
            "topic": st.session_state.topic,
            "steps": st.session_state.steps,
            "internal_sources": st.session_state.internal_sources,
            "external_sources": st.session_state.external_sources,
        }
        
        with st.spinner("Executing research plan... This may take a few minutes."):
            resp = requests.post(f"{API_URL}/execute/", json={"plan": plan_to_send}, timeout=120)
        
        if resp.status_code != 200:
            st.error(f"Research execution failed [{resp.status_code}]: {resp.text}")
            st.stop()
        
        # Check if response has content
        if not resp.content:
            st.error("Received empty response from server. Please try again.")
            st.stop()
        
        # Save as DOCX file instead of PDF
        try:
            with open("report.docx", "wb") as f:
                f.write(resp.content)
            
            # Verify file was written
            import os
            if os.path.exists("report.docx") and os.path.getsize("report.docx") > 0:
                st.session_state.step = 2
                st.success("Research completed successfully!")
                st.rerun()
            else:
                st.error("Failed to save report file. Please try again.")
                
        except Exception as e:
            st.error(f"Failed to save report file: {str(e)}")
            
    except requests.Timeout:
        st.error("Research execution timed out. Please try again with a simpler plan.")
    except requests.ConnectionError:
        st.error("Could not connect to the backend server. Please ensure it's running on port 8082.")
    except Exception as e:
        st.error(f"Research execution failed: {str(e)}")


# UI flow
if st.session_state.step == 0:
    st.markdown("### Enter Your Research Topic")
    
    topic = st.text_input(
        "What would you like to research?",
        placeholder="e.g., Responsible AI practices",
        help="Enter any topic you'd like to research. Be specific for better results."
    )
    
    if st.button("Generate Research Plan", type="primary", disabled=not topic.strip()):
        if len(topic.strip()) < 5:
            st.error("Please enter a more detailed research topic (at least 5 characters).")
            st.stop()
            
        try:
            with st.spinner("Generating research plan... This may take a moment."):
                resp = requests.post(f"{API_URL}/plan/", json={"topic": topic}, timeout=60)
            
            if resp.status_code != 200:
                st.error(f"Plan generation failed [{resp.status_code}]: {resp.text}")
            else:
                plan = resp.json().get("plan", {})
                if not plan:
                    st.error("Received empty plan from server. Please try again.")
                    st.stop()
                    
                init_plan_state(plan)
                st.session_state.step = 1
                st.session_state.edit_mode = False
                st.success("Research plan generated successfully!")
                st.rerun()
                
        except requests.Timeout:
            st.error("Plan generation timed out. Please try again with a simpler topic.")
        except requests.ConnectionError:
            st.error("Could not connect to the backend server. Please ensure it's running on port 8082.")
        except Exception as e:
            st.error(f"Plan generation failed: {str(e)}")


elif st.session_state.step == 1:
    if 'plan' not in st.session_state:
        st.error("No plan in session. Please generate a plan again.")
        if st.button("Start Over"):
            st.session_state.step = 0
            st.rerun()
    else:
        render_plan_review()


elif st.session_state.step == 2:
    st.success("Your research report is ready!")
    
    # Add some visual elements
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        st.metric("Research Topic", st.session_state.topic)
    
    with col2:
        st.metric("Research Steps", len(st.session_state.steps))
    
    with col3:
        import os
        if os.path.exists("report.docx"):
            file_size = os.path.getsize("report.docx")
            st.metric("Report Size", f"{file_size / 1024:.1f} KB")
    
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### Download Your Report")
        st.write("Your research report has been generated.")

    
    with col2:
        try:
            with open("report.docx", "rb") as f:
                # Create a safe filename
                safe_topic = "".join(c for c in st.session_state.topic if c.isalnum() or c in (' ', '_', '-')).strip()
                safe_topic = safe_topic.replace(' ', '_').lower()
                filename = f"research_report_{safe_topic}.docx"
                
                st.download_button(
                    "Download Report",
                    data=f,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    help="Click to download your research report as a Word document"
                )
        except FileNotFoundError:
            st.error("Report file not found. Please try generating the report again.")
            if st.button("Regenerate Report"):
                st.session_state.step = 1
                st.rerun()
        except Exception as e:
            st.error(f"Error accessing report file: {str(e)}")
    
    st.markdown("---")
    
    # Add research summary
    with st.expander("📊 Research Summary"):
        st.write(f"**Topic:** {st.session_state.topic}")
        st.write(f"**Number of research steps:** {len(st.session_state.steps)}")
        
        if st.session_state.internal_sources:
            st.write(f"**Internal sources used:** {len(st.session_state.internal_sources)}")
            for i, source in enumerate(st.session_state.internal_sources[:3], 1):
                st.write(f"  {i}. {source.get('title', 'Unknown Document')}")
            if len(st.session_state.internal_sources) > 3:
                st.write(f"  ... and {len(st.session_state.internal_sources) - 3} more")
        
        st.write("**Research steps executed:**")
        for i, step in enumerate(st.session_state.steps, 1):
            st.write(f"  {i}. {step.get('query', '')}")
    
    # Action buttons
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        if st.button("Start New Research"):
            # Clean up old report file
            try:
                import os
                if os.path.exists("report.docx"):
                    os.remove("report.docx")
            except:
                pass
            
            # Clear session state
            for key in ['plan', 'topic', 'internal_sources', 'external_sources', 'steps', 'edit_mode']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.step = 0
            st.rerun()
    
    with col2:
        if st.button("Modify This Research"):
            st.session_state.step = 1
            st.session_state.edit_mode = True
            st.rerun()
    
    with col3:
        if st.button("Regenerate Report"):
            st.session_state.step = 1
            st.info("You can modify your research plan and generate a new report.")
            st.rerun()


# Add footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
    Research Assistant - Powered by AI | Generate comprehensive research reports with internal and external sources
    </div>
    """, 
    unsafe_allow_html=True
)

# Add some custom CSS for better styling
st.markdown("""
<style>
    .stButton > button {
        border-radius: 5px;
    }
    .stDownloadButton > button {
        background-color: #0066cc;
        color: white;
        border-radius: 5px;
    }
    .stAlert {
        border-radius: 5px;
    }
    .stSuccess {
        border-left: 5px solid #28a745;
    }
    .stError {
        border-left: 5px solid #dc3545;
    }
    .stInfo {
        border-left: 5px solid #17a2b8;
    }
    .stWarning {
        border-left: 5px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)
