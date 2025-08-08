import streamlit as st
import requests
import json

API_URL = "http://localhost:8083"

st.set_page_config(page_title="Agentic Research Assistant", layout="wide")
st.title("Agentic Research Assistant")

if 'step' not in st.session_state:
    st.session_state.step = 0

def init_plan_state(plan):
    # Initialize structured state from backend plan only once
    st.session_state.plan = plan
    st.session_state.topic = plan.get("topic", "")
    st.session_state.plan_text = plan.get("plan_text", "")
    st.session_state.internal_sources = plan.get("internal_sources", [])
    st.session_state.external_sources = plan.get("external_sources", [])
    # Steps for editing
    st.session_state.steps = plan.get("steps", [])

def render_sources_section():
    st.subheader("Suggested Internal Sources")
    ints = st.session_state.internal_sources or []
    if ints:
        for s in ints:
            st.write(f"- {s.get('title','')} ({s.get('type','')})")
    else:
        st.write("- None")

    st.subheader("Suggested External Sources")
    exts = st.session_state.external_sources or []
    if exts:
        for s in exts:
            note = s.get("note", "")
            note_str = f" — {note}" if note else ""
            st.write(f"- {s.get('name','')} ({s.get('type','')}){note_str}")
    else:
        st.write("- None")

# # --- Structured Steps Editor (drop-in) ---

# def render_structured_steps():
#     st.subheader("Research Steps (Edit)")

#     # Add Step button (single column)
#     add_col = st.columns(1)[0]
#     with add_col:
#         if st.button("➕ Add Step"):
#             st.session_state.steps.append({"agent": "external", "query": "", "needs": []})
#             st.rerun()

#     if not st.session_state.steps:
#         st.info("No steps yet. Click 'Add Step' to create one.")
#         return

#     for i, step in enumerate(st.session_state.steps):
#         st.markdown(f"Step {i+1}")
#         c_agent, c_query, c_needs, c_up, c_down = st.columns([1.2, 4, 3, 1.2, 1.2])

#         # Agent selector
#         with c_agent:
#             agent = st.selectbox(
#                 "Agent",
#                 options=["internal", "external"],
#                 index=(0 if step.get("agent") == "internal" else 1),
#                 key=f"agent_{i}"
#             )
#             step["agent"] = agent

#         # Query input
#         with c_query:
#             query = st.text_input("Query", value=step.get("query", ""), key=f"query_{i}")
#             step["query"] = query

#         # Needs checkbox (kept for structure; you can ignore on backend)
#         with c_needs:
#             want_image = "Image" in (step.get("needs") or [])
#             want_image = st.checkbox("Needs Image", value=want_image, key=f"needs_image_{i}")
#             step["needs"] = ["Image"] if want_image else []

#         # Reorder Up
#         with c_up:
#             if st.button("⬆️", key=f"up_{i}", help="Move up") and i > 0:
#                 st.session_state.steps[i-1], st.session_state.steps[i] = st.session_state.steps[i], st.session_state.steps[i-1]
#                 st.rerun()

#         # Reorder Down
#         with c_down:
#             if st.button("⬇️", key=f"down_{i}", help="Move down") and i < len(st.session_state.steps)-1:
#                 st.session_state.steps[i+1], st.session_state.steps[i] = st.session_state.steps[i], st.session_state.steps[i+1]
#                 st.rerun()

#         # Remove Step (place under the row)
#         if st.button("🗑️ Remove Step", key=f"remove_{i}"):
#             st.session_state.steps.pop(i)
#             st.rerun()


# --- Plan Review with Raw JSON Text Box (drop-in) ---

def render_plan_review_with_textbox():
    # Display readable plan text and suggested sources
    st.subheader("Proposed Research Plan")
    st.write(st.session_state.get("plan_text", "") or st.session_state.plan.get("plan_text", ""))

    st.subheader("Suggested Internal Sources")
    ints = st.session_state.get("internal_sources") or st.session_state.plan.get("internal_sources", []) or []
    if ints:
        for s in ints:
            st.write(f"- {s.get('title','')} ({s.get('type','')})")
    else:
        st.write("- None")

    st.subheader("Suggested External Sources")
    exts = st.session_state.get("external_sources") or st.session_state.plan.get("external_sources", []) or []
    if exts:
        for s in exts:
            note = s.get("note", "")
            note_str = f" — {note}" if note else ""
            st.write(f"- {s.get('name','')} ({s.get('type','')}){note_str}")
    else:
        st.write("- None")

    st.markdown("---")
    st.subheader("Edit Plan (JSON)")
    # Pre-fill JSON with the whole plan object so backend /execute gets what it expects
    plan_obj = {
        "topic": st.session_state.get("topic") or st.session_state.plan.get("topic", ""),
        "plan_text": st.session_state.get("plan_text") or st.session_state.plan.get("plan_text", ""),
        "steps": st.session_state.get("steps") or st.session_state.plan.get("steps", []),
        "internal_sources": st.session_state.get("internal_sources") or st.session_state.plan.get("internal_sources", []),
        "external_sources": st.session_state.get("external_sources") or st.session_state.plan.get("external_sources", []),
    }
    plan_str_default = json.dumps(plan_obj, indent=2)
    edited_plan_str = st.text_area("Plan JSON", plan_str_default, height=350)

    st.markdown("---")
    if st.button("Proceed with Research"):
        try:
            json_plan = json.loads(edited_plan_str)
            # Optional: basic validation
            if not isinstance(json_plan, dict) or "topic" not in json_plan or "steps" not in json_plan:
                st.error("Plan JSON must include 'topic' and 'steps'.")
                return
            resp = requests.post(f"{API_URL}/execute/", json={"plan": json_plan}, timeout=90)
            if resp.status_code != 200:
                st.error(f"Execution failed [{resp.status_code}]: {resp.text}")
            else:
                with open("report.pdf", "wb") as f:
                    f.write(resp.content)
                st.session_state.step = 2
                st.rerun()
        except json.JSONDecodeError:
            st.error("Invalid JSON in plan. Please fix and try again.")
        except requests.Timeout:
            st.error("Execution timed out. Please try again or simplify the plan.")
        except Exception as e:
            st.error(f"Execution failed: {e}")


def render_execute_button():
    st.markdown("---")
    if st.button("Proceed with Research"):
        try:
            # Build plan JSON to send to backend
            plan_to_send = {
                "topic": st.session_state.topic,
                "plan_text": st.session_state.plan_text,
                "steps": st.session_state.steps,
                "internal_sources": st.session_state.internal_sources,
                "external_sources": st.session_state.external_sources,
            }
            resp = requests.post(f"{API_URL}/execute/", json={"plan": plan_to_send}, timeout=90)
            if resp.status_code != 200:
                st.error(f"Execution failed [{resp.status_code}]: {resp.text}")
            else:
                with open("report.pdf", "wb") as f:
                    f.write(resp.content)
                st.session_state.step = 2
                st.rerun()
        except requests.Timeout:
            st.error("Execution timed out. Please refine the plan or try again.")
        except Exception as e:
            st.error(f"Execution failed: {e}")

# UI flow
if st.session_state.step == 0:
    topic = st.text_input("Enter the research topic:")
    if st.button("Generate Research Plan") and topic:
        try:
            resp = requests.post(f"{API_URL}/plan/", json={"topic": topic}, timeout=60)
            if resp.status_code != 200:
                st.error(f"Plan failed [{resp.status_code}]: {resp.text}")
            else:
                plan = resp.json().get("plan", {})
                init_plan_state(plan)
                st.session_state.step = 1
                st.rerun()
        except requests.Timeout:
            st.error("Plan request timed out (client). Try again.")
        except Exception as e:
            st.error(f"Plan generation failed: {e}")

elif st.session_state.step == 1:
    # Ensure plan is in session_state
    if 'plan' not in st.session_state:
        st.error("No plan in session. Please generate a plan again.")
    else:
        # Keep topic/plan_text/sources/steps in state for convenience
        st.session_state.topic = st.session_state.plan.get("topic", "")
        st.session_state.plan_text = st.session_state.plan.get("plan_text", "")
        st.session_state.internal_sources = st.session_state.plan.get("internal_sources", [])
        st.session_state.external_sources = st.session_state.plan.get("external_sources", [])
        st.session_state.steps = st.session_state.plan.get("steps", [])

        render_plan_review_with_textbox()

elif st.session_state.step == 2:
    st.success("Your research report is ready!")
    with open("report.pdf", "rb") as f:
        st.download_button("Download PDF", data=f, file_name="research_report.pdf", mime="application/pdf")
