import os
import base64
import time
import json
import threading
import yaml
import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
from pipeline import DocumentPipeline

st.set_page_config(layout="wide", page_title="PDF to Markdown Converter")

# Custom CSS for the premium Dark/Glassmorphic Theme
st.html("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif;
        background: radial-gradient(circle at top right, #1a1a2e, #0f0f16);
        color: #e2e8f0;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #8b5cf6, #3b82f6) !important;
        color: white !important;
        border: none !important;
        padding: 10px 24px !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 0 15px rgba(139, 92, 246, 0.4) !important;
    }
    
    .pipeline-stepper {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 20px 0 35px 0;
        padding: 24px;
        background: rgba(22, 22, 34, 0.4);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
    }
    .step-node {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        flex: 1;
    }
    .step-node::after {
        content: '';
        position: absolute;
        top: 20px;
        left: 50%;
        width: 100%;
        height: 2px;
        background: rgba(255, 255, 255, 0.06);
        z-index: 1;
    }
    .step-node:last-child::after {
        display: none;
    }
    .step-node.completed::after {
        background: linear-gradient(90deg, #10b981, #8b5cf6);
    }
    .step-circle {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: #11111a;
        border: 2px solid rgba(255, 255, 255, 0.1);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 2;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .step-node.active .step-circle {
        border-color: #8b5cf6;
        box-shadow: 0 0 20px rgba(139, 92, 246, 0.4);
        background: #8b5cf6;
        color: white;
        z-index: 3;
    }
    .step-node.completed .step-circle {
        border-color: #10b981;
        background: #10b981;
        color: white;
        z-index: 3;
    }
    .step-label {
        margin-top: 10px;
        font-size: 0.85rem;
        font-weight: 500;
        color: #64748b;
        transition: color 0.3s ease;
    }
    .step-node.active .step-label {
        color: #e2e8f0;
    }
    .step-node.completed .step-label {
        color: #10b981;
    }
    
    .glass-card {
        background: rgba(30, 30, 46, 0.45);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
    }
    
    .page-status-card {
        background: rgba(22, 22, 34, 0.3);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 16px;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .page-status-card.active {
        border-color: #8b5cf6;
        background: rgba(139, 92, 246, 0.05);
        box-shadow: 0 0 12px rgba(139, 92, 246, 0.15);
    }
    .page-status-card.completed {
        border-color: #10b981;
        background: rgba(16, 185, 129, 0.05);
    }
    .page-status-card.failed {
        border-color: #ef4444;
        background: rgba(239, 68, 68, 0.05);
    }

    .meta-pill-container {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin: 14px 0;
    }
    .meta-pill {
        background: rgba(139, 92, 246, 0.08);
        border: 1px solid rgba(139, 92, 246, 0.18);
        color: #c084fc;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
    }
    .summary-box {
        background: rgba(255, 255, 255, 0.015);
        border-left: 4px solid #8b5cf6;
        border-radius: 0 12px 12px 0;
        padding: 18px 22px;
        margin: 18px 0;
        font-style: italic;
        color: #cbd5e1;
        line-height: 1.6;
        font-size: 0.95rem;
    }
    .dashboard-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #f8fafc, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }
</style>
""")

def render_stepper(current_step: str):
    """Renders the top navigation progress tracker tracker without markdown spacing bugs."""
    steps = [
        ("upload", "1", "Upload File"),
        ("verify", "2", "Verify Metadata"),
        ("parse", "3", "Conversion Pipeline"),
        ("results", "4", "Export & Preview")
    ]
    current_index = [s[0] for s in steps].index(current_step)
    
    step_flow_html = '<div class="pipeline-stepper">'
    for idx, (step_key, step_num, label) in enumerate(steps):
        status_class = ""
        if idx < current_index:
            status_class = "completed"
        elif idx == current_index:
            status_class = "active"
        step_flow_html += f'<div class="step-node {status_class}"><div class="step-circle">{step_num}</div><div class="step-label">{label}</div></div>'
    step_flow_html += '</div>'
    st.html(step_flow_html)

# Session State Initialization
if "step" not in st.session_state:
    st.session_state.step = "upload"
if "base64_pages" not in st.session_state:
    st.session_state.base64_pages = []
if "metadata" not in st.session_state:
    st.session_state.metadata = {}
if "markdown_output" not in st.session_state:
    st.session_state.markdown_output = ""
if "pipeline_running" not in st.session_state:
    st.session_state.pipeline_running = False
if "page_outputs" not in st.session_state:
    st.session_state.page_outputs = {}
if "page_status" not in st.session_state:
    st.session_state.page_status = {}
if "page_errors" not in st.session_state:
    st.session_state.page_errors = {}
if "telemetry" not in st.session_state:
    st.session_state.telemetry = {
        "metadata_input_tokens": 0,
        "metadata_output_tokens": 0,
        "page_input_tokens": {},
        "page_output_tokens": {},
        "pipeline_start_time": 0.0,
        "pipeline_end_time": 0.0,
    }
if "telemetry_summary" not in st.session_state:
    st.session_state.telemetry_summary = {}

# Sidebar settings
st.sidebar.title("Pipeline Settings")

# Check environment key first to bypass browser password autofill issues
env_key = os.getenv("GEMINI_API_KEY", "").strip()
if env_key:
    masked_key = env_key[:6] + "..." + env_key[-4:] if len(env_key) > 10 else "Active"
    st.sidebar.success(f"🔑 System Key Active ({masked_key})")
    api_key = env_key
else:
    api_key = st.sidebar.text_input("Gemini API Key", value="", type="password")

model = st.sidebar.selectbox("Gemini Model Choice", ["gemini-3.5-flash", "gemini-2.5-pro", "gemini-2.5-flash"])

if not api_key:
    st.sidebar.warning("Please configure your Gemini API Key in the sidebar.")
elif api_key.startswith("sk-or-v1"):
    st.sidebar.error("⚠️ OpenRouter key detected. Please use a direct Gemini API key starting with 'AIzaSy' from Google AI Studio.")

# Local Telemetry Logging Function
def log_run_telemetry(model_name: str, num_pages: int, title: str):
    telemetry = st.session_state.telemetry
    
    meta_in = telemetry.get("metadata_input_tokens", 0)
    meta_out = telemetry.get("metadata_output_tokens", 0)
    
    page_in = sum(telemetry.get("page_input_tokens", {}).values())
    page_out = sum(telemetry.get("page_output_tokens", {}).values())
    
    total_in = meta_in + page_in
    total_out = meta_out + page_out
    
    # 2026 Direct Gemini API token rates per 1M tokens
    if "pro" in model_name:
        input_rate = 1.25 / 1_000_000
        output_rate = 5.00 / 1_000_000
    else:
        # Default to Flash tier pricing
        input_rate = 0.075 / 1_000_000
        output_rate = 0.30 / 1_000_000
        
    cost = (total_in * input_rate) + (total_out * output_rate)
    
    start_time = telemetry.get("pipeline_start_time", 0.0)
    end_time = telemetry.get("pipeline_end_time", 0.0)
    latency = end_time - start_time if start_time and end_time else 0.0
    
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "document_title": title,
        "pages": num_pages,
        "model": model_name,
        "input_tokens": total_in,
        "output_tokens": total_out,
        "total_tokens": total_in + total_out,
        "cost_usd": cost,
        "latency_seconds": latency
    }
    
    try:
        log_path = os.path.join(os.getcwd(), "telemetry_log.jsonl")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
        
    st.session_state.telemetry_summary = log_entry

# Background thread worker function
def worker_convert_page(api_key: str, model: str, page_b64: str, page_idx: int):
    try:
        st.session_state.page_status[page_idx] = "processing"
        pipeline = DocumentPipeline(api_key, model)
        
        # Get streaming generator
        stream = pipeline.convert_page_to_markdown_stream(page_b64, page_idx + 1)
        for chunk in stream:
            if chunk.text:
                st.session_state.page_outputs[page_idx] += chunk.text
            if chunk.usage_metadata:
                st.session_state.telemetry["page_input_tokens"][page_idx] = chunk.usage_metadata.prompt_token_count
                st.session_state.telemetry["page_output_tokens"][page_idx] = chunk.usage_metadata.candidates_token_count
            
        st.session_state.page_status[page_idx] = "done"
    except Exception as e:
        st.session_state.page_status[page_idx] = "failed"
        st.session_state.page_errors[page_idx] = str(e)

def run_parallel_pipeline(api_key: str, model: str, base64_pages: list[str]):
    st.session_state.pipeline_running = True
    st.session_state.page_outputs = {i: "" for i in range(len(base64_pages))}
    st.session_state.page_status = {i: "pending" for i in range(len(base64_pages))}
    st.session_state.page_errors = {}
    st.session_state.telemetry["page_input_tokens"] = {}
    st.session_state.telemetry["page_output_tokens"] = {}
    st.session_state.telemetry["pipeline_start_time"] = time.time()
    
    threads = []
    for idx, page_b64 in enumerate(base64_pages):
        t = threading.Thread(
            target=worker_convert_page,
            args=(api_key, model, page_b64, idx)
        )
        add_script_run_ctx(t)
        threads.append(t)
        
    for t in threads:
        t.start()

# SCREEN 1: Upload PDF
if st.session_state.step == "upload":
    st.title("📂 Upload Document")
    render_stepper("upload")
    
    uploaded_file = st.file_uploader("Drag and drop your PDF here", type=["pdf"])
    
    if uploaded_file and api_key:
        if st.button("Begin Processing"):
            pipeline = DocumentPipeline(api_key, model)
            try:
                with st.spinner("Rendering PDF pages locally..."):
                    st.session_state.base64_pages = pipeline.pdf_to_base64_images(uploaded_file)
                
                with st.spinner("Extracting document metadata..."):
                    metadata_res, meta_in, meta_out = pipeline.extract_metadata(st.session_state.base64_pages)
                    st.session_state.metadata = metadata_res
                    st.session_state.telemetry["metadata_input_tokens"] = meta_in
                    st.session_state.telemetry["metadata_output_tokens"] = meta_out
                    
                st.session_state.step = "verify"
                st.rerun()
            except Exception as e:
                st.error(f"❌ Extraction failed. Please verify your Gemini API key and try again.\n\nError details: {str(e)}")

# SCREEN 2: Metadata Verification
elif st.session_state.step == "verify":
    st.title("🛡️ Verify & Refine Metadata")
    render_stepper("verify")
    st.write("Gemini detected the following metadata. Please review and update before running full extraction.")
    
    with st.form("metadata_form"):
        title = st.text_input("Document Title", value=st.session_state.metadata.get("title", ""))
        doc_date = st.text_input("Document Date (YYYY-MM-DD)", value=st.session_state.metadata.get("doc_date", ""))
        category = st.selectbox("Category", ["Project Schedule", "Bid/Proposal", "Technical Spec", "Financial Report", "Meeting Minutes", "Other"], 
                                index=0)
        author_org = st.text_input("Author / Organization", value=st.session_state.metadata.get("author_org", ""))
        summary = st.text_area("Executive Summary", value=st.session_state.metadata.get("summary", ""))
        
        submitted = st.form_submit_button("Confirm & Generate Full Markdown")
        
        if submitted:
            st.session_state.metadata = {
                "title": title,
                "doc_date": doc_date,
                "category": category,
                "author_org": author_org,
                "summary": summary,
                "visuals_detected": st.session_state.metadata.get("visuals_detected", []),
                "confidence_score": st.session_state.metadata.get("confidence_score", "High")
            }
            st.session_state.step = "parse"
            st.rerun()

# SCREEN 3: Parse Document & Output (Live Parallel Progress Tracking)
elif st.session_state.step == "parse":
    st.title("⚡ Conversion Pipeline")
    render_stepper("parse")
    
    num_pages = len(st.session_state.base64_pages)
    
    # Start the parallel worker pipeline if not running
    if not st.session_state.pipeline_running:
        run_parallel_pipeline(api_key, model, st.session_state.base64_pages)
        st.rerun()
        
    # Split layout: 5/8 wide for active feeds, 3/8 wide for thumbnails list on the right
    left_col, right_col = st.columns([5, 3])
    
    with left_col:
        st.write("### ⚡ Live Streaming Feeds")
        
        # Create tabs to display streaming output per page (Placed at the top of the fold!)
        tabs = st.tabs([f"Page {i+1}" for i in range(num_pages)])
        for idx, tab in enumerate(tabs):
            with tab:
                status = st.session_state.page_status.get(idx, "pending")
                out_text = st.session_state.page_outputs.get(idx, "")
                
                if status == "processing":
                    st.info("Streaming in progress...")
                elif status == "done":
                    st.success("Conversion complete!")
                elif status == "failed":
                    st.error(f"Failed: {st.session_state.page_errors.get(idx)}")
                    
                sub_tabs = st.tabs(["Rendered Preview", "Raw Markdown Code"])
                with sub_tabs[0]:
                    st.markdown(out_text if out_text else "*Waiting for conversion...*")
                with sub_tabs[1]:
                    st.code(out_text if out_text else "Waiting for conversion...", language="markdown")
                    
    with right_col:
        st.write("### 📋 Document Pages")
        
        # Draw vertical status items with compact thumbnails
        for idx, page_b64 in enumerate(st.session_state.base64_pages):
            status = st.session_state.page_status.get(idx, "pending")
            err = st.session_state.page_errors.get(idx, "")
            
            card_class = ""
            status_text = "Queued"
            status_emoji = "💤"
            
            if status == "processing":
                card_class = "active"
                status_text = "Processing..."
                status_emoji = "⚡"
            elif status == "done":
                card_class = "completed"
                status_text = "Completed"
                status_emoji = "✅"
            elif status == "failed":
                card_class = "failed"
                status_text = "Error"
                status_emoji = "❌"
                
            st.html(f'<div class="page-status-card {card_class}" style="margin-bottom: 8px; padding: 12px; text-align: left;"><div style="font-size: 1rem; font-weight: 600;">Page {idx + 1}</div><div style="font-size: 0.8rem; color: #94a3b8;">{status_emoji} {status_text}</div></div>')
            
            # Show compact thumbnail preview (Limit width to 180px so it fits side-by-side or inside card)
            try:
                st.image(base64.b64decode(page_b64), width=180)
            except Exception:
                pass
            st.write("") # Spacer between pages

    # Check if all processes are completed or failed
    all_finished = all(status in ["done", "failed"] for status in st.session_state.page_status.values())
    
    if not all_finished:
        time.sleep(0.5)
        st.rerun()
    else:
        # All pages are finished, stitch results together
        st.session_state.pipeline_running = False
        st.session_state.telemetry["pipeline_end_time"] = time.time()
        
        frontmatter = yaml.dump(st.session_state.metadata, default_flow_style=False, allow_unicode=True)
        
        markdown_pages = []
        for idx in range(num_pages):
            if st.session_state.page_status[idx] == "done":
                markdown_pages.append(st.session_state.page_outputs[idx])
            else:
                markdown_pages.append(f"\n\n> [!ERROR] Page {idx+1} conversion failed: {st.session_state.page_errors.get(idx)}\n\n")
                
        final_output = f"---\n{frontmatter}---\n\n" + "\n\n---\n\n".join(markdown_pages)
        st.session_state.markdown_output = final_output
        
        # Log run telemetry
        log_run_telemetry(model, num_pages, st.session_state.metadata.get("title", "Structured Document"))
        
        st.session_state.step = "results"
        st.rerun()

# SCREEN 4: Display & Save results
elif st.session_state.step == "results":
    st.title("🎉 Conversion Complete!")
    render_stepper("results")
    
    # Metadata Dashboard Header Card
    title = st.session_state.metadata.get("title", "Structured Document")
    doc_date = st.session_state.metadata.get("doc_date", "N/A")
    category = st.session_state.metadata.get("category", "Document")
    author_org = st.session_state.metadata.get("author_org", "N/A")
    summary = st.session_state.metadata.get("summary", "")
    confidence = st.session_state.metadata.get("confidence_score", "High")
    
    st.html(f"""
        <div class="glass-card">
            <div class="dashboard-header">{title}</div>
            <div class="meta-pill-container">
                <span class="meta-pill">📂 Category: {category}</span>
                <span class="meta-pill">📅 Date: {doc_date}</span>
                <span class="meta-pill">🏢 Org: {author_org}</span>
                <span class="meta-pill">🎯 Confidence: {confidence}</span>
            </div>
            <div class="summary-box">
                <strong>Executive Summary:</strong><br>{summary}
            </div>
        </div>
    """.replace('\n', '').replace('  ', ''))
    
    # Usage Telemetry Metrics Card
    usage = st.session_state.get("telemetry_summary", {})
    if usage:
        st.subheader("📊 Performance & Telemetry metrics")
        col_t, col_c, col_l = st.columns(3)
        with col_t:
            st.metric(
                label="Total Tokens Consumed",
                value=f"{usage.get('total_tokens', 0):,}",
                delta=f"In: {usage.get('input_tokens', 0):,} | Out: {usage.get('output_tokens', 0):,}",
                delta_color="off"
            )
        with col_c:
            st.metric(
                label="Estimated Call Cost",
                value=f"${usage.get('cost_usd', 0.0):.5f}",
                delta="Gemini API direct pricing",
                delta_color="off"
            )
        with col_l:
            st.metric(
                label="Wall-clock Processing Speed",
                value=f"{usage.get('latency_seconds', 0.0):.2f}s",
                delta=f"Avg: {usage.get('latency_seconds', 0.0)/usage.get('pages', 1):.2f}s / page",
                delta_color="inverse"
            )
        st.write("---")
        
    # Render Output Tabs
    tabs = st.tabs(["✨ Rendered Document", "💻 Raw Markdown Code"])
    
    with tabs[0]:
        st.markdown(st.session_state.markdown_output)
        
    with tabs[1]:
        st.code(st.session_state.markdown_output, language="markdown")
        
    st.write("---")
    
    # Export Options
    col1, col2 = st.columns([3, 1])
    with col1:
        st.download_button(
            label="📥 Download Structured Markdown File (.md)",
            data=st.session_state.markdown_output,
            file_name=f"{title.replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True
        )
    with col2:
        if st.button("🔄 Start New File", use_container_width=True):
            st.session_state.step = "upload"
            st.session_state.base64_pages = []
            st.session_state.metadata = {}
            st.session_state.markdown_output = ""
            st.session_state.page_outputs = {}
            st.session_state.page_status = {}
            st.session_state.page_errors = {}
            st.session_state.telemetry = {
                "metadata_input_tokens": 0,
                "metadata_output_tokens": 0,
                "page_input_tokens": {},
                "page_output_tokens": {},
                "pipeline_start_time": 0.0,
                "pipeline_end_time": 0.0,
            }
            st.session_state.telemetry_summary = {}
            st.rerun()
