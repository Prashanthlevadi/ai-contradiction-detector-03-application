"""AI Contradiction Detector — Complete Application (Stage 3).

Official Reference: PDF 04 Application Build, UI, Evidence Display & Error Flows.

Features:
- Dual-source input (PDF upload, raw text, and pre-packaged synthetic datasets).
- Multi-stage pipeline: PyMuPDF extraction -> Cleaner -> Claims -> Alignment -> Comparison.
- Evidence display with verbatim source sentences, confidence heuristics, and human verification badges.
- Summary metrics dashboard.
- Safe error handling flow with secret redaction and OCR diagnosis.
- SQLite audit history.
"""

import sys
import os
import json
import streamlit as st

# Ensure application src is in python path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from src.pdf_reader import extract_text, inspect_pdf, PDFExtractionError
from src.cleaner import clean_text
from src.claims import Claim, extract_claims_rule_based
from src.matcher import find_candidate_pairs
from src.comparator import ComparisonResult, compare_claims_rule_based
from src.pipeline import ContradictionPipeline
from src.llm_client import LLMClient, redact_secrets
from src.errors import diagnose_inputs, ContradictionAppError, ZeroTextOCRError
from src.history import HistoryDB

st.set_page_config(
    page_title="AI Contradiction Detector",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics and clean typography
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border-left: 5px solid #0d6efd;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .contradiction-card {
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: #fff8f8;
        border: 1px solid #ffcdd2;
        border-left: 6px solid #e53935;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    .compatible-card {
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: #f6fbf7;
        border: 1px solid #c8e6c9;
        border-left: 6px solid #43a047;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    .badge-review {
        background-color: #fff3cd;
        color: #856404;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-consistent {
        background-color: #d4edda;
        color: #155724;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# Database instance
db = HistoryDB()

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Engine Configuration")
    provider_choice = st.selectbox(
        "LLM Provider Engine:",
        ["Deterministic Local Engine (Offline / Zero Token)", "Google Gemini API", "OpenAI API"],
        index=0
    )
    
    api_key_input = ""
    if "Gemini" in provider_choice:
        api_key_input = st.text_input("Gemini API Key:", type="password", placeholder="AIza...")
    elif "OpenAI" in provider_choice:
        api_key_input = st.text_input("OpenAI API Key:", type="password", placeholder="sk-...")

    st.markdown("---")
    st.markdown("### 🔒 Responsible AI Protocol")
    st.caption(
        "• System strictly labels conflicts as **'Potential Contradiction'**.\n"
        "• Defamatory or judicial accusations are prohibited.\n"
        "• All findings require human verification.\n"
        "• Confidence scores are heuristic estimates."
    )
    st.markdown("---")
    st.caption("AI Contradiction Detector • Stage 03 Application")

# Main Header
st.title("⚖️ AI Contradiction Detector")
st.markdown(
    "Cross-document factual verification engine. Extracts structured claims, aligns underlying topics, "
    "and detects discrepancies with verbatim evidence citations."
)

st.markdown("---")

# Input Section
st.subheader("1. Source Documents")

sample_pairs = {
    "Employment Record Conflict (Preset 1)": {
        "desc": "Detects tenure, project allocation, and location contradictions between a resume and background report.",
        "file_a": "sample_doc_a.pdf",
        "file_b": "sample_doc_b.pdf"
    },
    "Clean Verification (Preset 2)": {
        "desc": "Demonstrates compatible claims where both documents report identical facts.",
        "text_a": (
            "Candidate: Prashanth Levadi\n"
            "Company: ABC Technologies\n"
            "Role: AI Research Intern\n"
            "Employment Period: January 2024 to December 2024\n"
            "Project Budget: $50,000\n"
            "Degree: B.Tech in Computer Science\n"
            "City: Bengaluru, India\n"
        ),
        "text_b": (
            "Verified Employee: Prashanth Levadi\n"
            "Company: ABC Technologies\n"
            "Role: AI Research Intern\n"
            "Employment Dates: January 2024 to December 2024\n"
            "Project Allocation: $50,000\n"
            "Degree: B.Tech in Computer Science\n"
            "City: Bengaluru, India\n"
        )
    }
}

input_type = st.radio(
    "Choose input source:",
    ["Upload PDF Documents", "Use Synthetic Demonstration Presets", "Enter Custom Raw Text"],
    horizontal=True
)

text_a = ""
text_b = ""
diag_a = {}
diag_b = {}
label_a = "Source A (Primary)"
label_b = "Source B (Verification)"

samples_dir = os.path.join(APP_DIR, "data", "samples")

if input_type == "Upload PDF Documents":
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 📄 Source Document A")
        pdf_a = st.file_uploader("Upload PDF A", type=["pdf"], key="app_pdf_a")
        if pdf_a:
            raw_a = pdf_a.getvalue()
            diag_a = inspect_pdf(raw_a)
            if diag_a.get("warning"):
                st.warning(diag_a["warning"])
            try:
                text_a = clean_text(extract_text(raw_a))
                label_a = pdf_a.name
                st.success(f"Extracted {len(text_a)} chars ({diag_a.get('page_count')} pages)")
            except PDFExtractionError as exc:
                st.error(f"Error extracting PDF A: {exc}")

    with col2:
        st.markdown("##### 📄 Source Document B")
        pdf_b = st.file_uploader("Upload PDF B", type=["pdf"], key="app_pdf_b")
        if pdf_b:
            raw_b = pdf_b.getvalue()
            diag_b = inspect_pdf(raw_b)
            if diag_b.get("warning"):
                st.warning(diag_b["warning"])
            try:
                text_b = clean_text(extract_text(raw_b))
                label_b = pdf_b.name
                st.success(f"Extracted {len(text_b)} chars ({diag_b.get('page_count')} pages)")
            except PDFExtractionError as exc:
                st.error(f"Error extracting PDF B: {exc}")

elif input_type == "Use Synthetic Demonstration Presets":
    preset_choice = st.selectbox("Select Synthetic Demonstration Scenario:", list(sample_pairs.keys()))
    scenario = sample_pairs[preset_choice]
    st.info(scenario["desc"])

    if "file_a" in scenario:
        pa = os.path.join(samples_dir, scenario["file_a"])
        pb = os.path.join(samples_dir, scenario["file_b"])
        if os.path.exists(pa) and os.path.exists(pb):
            with open(pa, "rb") as f:
                ba = f.read()
                diag_a = inspect_pdf(ba)
                text_a = clean_text(extract_text(ba))
            with open(pb, "rb") as f:
                bb = f.read()
                diag_b = inspect_pdf(bb)
                text_b = clean_text(extract_text(bb))
            label_a = scenario["file_a"]
            label_b = scenario["file_b"]
            st.success("Loaded synthetic demonstration PDF files.")
    else:
        text_a = clean_text(scenario["text_a"])
        text_b = clean_text(scenario["text_b"])
        label_a = "Clean Document A"
        label_b = "Clean Document B"
        st.success("Loaded clean synthetic demonstration records.")

else:  # Custom Raw Text
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 📄 Source A Content")
        raw_a = st.text_area("Paste document A text", height=180, key="raw_a")
        text_a = clean_text(raw_a)
    with col2:
        st.markdown("##### 📄 Source B Content")
        raw_b = st.text_area("Paste document B text", height=180, key="raw_b")
        text_b = clean_text(raw_b)

# Document previews
if text_a or text_b:
    with st.expander("👁️ View Extracted Document Previews", expanded=False):
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            st.caption(f"**{label_a}** ({len(text_a)} characters):")
            st.code(text_a or "(Empty)", language="text")
        with pcol2:
            st.caption(f"**{label_b}** ({len(text_b)} characters):")
            st.code(text_b or "(Empty)", language="text")

st.markdown("---")
st.subheader("2. Analysis Pipeline")

run_button = st.button("🚀 Run Contradiction Analysis", type="primary", use_container_width=True)

if run_button:
    # Error checking according to Step 8
    try:
        diagnose_inputs(text_a, text_b, diag_a, diag_b)
    except ZeroTextOCRError as ocr_err:
        st.error(f"❌ OCR Limitation Error: {ocr_err.user_friendly_message}")
        st.stop()
    except ContradictionAppError as app_err:
        st.warning(f"⚠️ Input Notice: {app_err.user_friendly_message}")
        st.stop()

    with st.spinner("Processing pipeline: Extracting claims -> Aligning topics -> Comparing evidence..."):
        pipeline = ContradictionPipeline(use_rule_engine=True)
        results_data = pipeline.process_texts(text_a, text_b, label_a=label_a, label_b=label_b)

        claims_a = results_data["claims_a"]
        claims_b = results_data["claims_b"]
        results = results_data["results"]
        metrics = results_data["metrics"]

        # Record in SQLite history
        try:
            db.record_run(label_a, label_b, metrics, results)
        except Exception as exc:
            st.caption(f"Note: Could not record SQLite history: {exc}")

    # Display KPI Metrics Dashboard (Step 7)
    st.markdown("### 📊 Verification Metrics")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric(label="Potential Contradictions", value=metrics["contradictions"], delta=None if metrics["contradictions"] == 0 else f"{metrics['contradictions']} flagged", delta_color="inverse")
    with m2:
        st.metric(label="Compatible Facts", value=metrics["compatible"])
    with m3:
        st.metric(label="Insufficient Data", value=metrics["insufficient"])
    with m4:
        st.metric(label="Claims Analyzed", value=metrics["claims_analyzed"])
    with m5:
        st.metric(label="Sources Processed", value=metrics["sources_processed"])

    st.markdown("---")

    # Tabs for structured viewing
    tab_contra, tab_compat, tab_claims, tab_history = st.tabs([
        f"⚠️ Potential Contradictions ({metrics['contradictions']})",
        f"✅ Compatible Claims ({metrics['compatible']})",
        f"📋 Extracted Claims ({metrics['claims_analyzed']})",
        "📜 Audit History"
    ])

    with tab_contra:
        contradictions = [r for r in results if r.classification == "contradiction"]
        if not contradictions:
            st.success("🎉 No contradictions detected! The compared facts are consistent across both documents.")
        else:
            st.info("The following claims exhibit conflicting values and require human verification.")
            for idx, item in enumerate(contradictions, 1):
                st.markdown(f"""
                <div class="contradiction-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <span style="color: #b71c1c; font-weight: 700; font-size: 1.05rem;">
                            ⚠️ POTENTIAL CONTRADICTION #{idx}
                        </span>
                        <span class="badge-review">Status: {item.status}</span>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Topic:</strong> <code>{item.topic.replace('_', ' ').title()}</code> &nbsp;|&nbsp; 
                        <strong>Confidence:</strong> {item.confidence * 100:.1f}% <em>(Model estimate)</em>
                    </div>
                    <div style="background-color: #ffffff; padding: 12px; border-radius: 6px; margin-bottom: 10px; border: 1px solid #eeeeee;">
                        <strong style="color: #1a237e;">Source A Evidence ({label_a}):</strong><br>
                        <em>"{item.source_a}"</em>
                    </div>
                    <div style="background-color: #ffffff; padding: 12px; border-radius: 6px; margin-bottom: 10px; border: 1px solid #eeeeee;">
                        <strong style="color: #1a237e;">Source B Evidence ({label_b}):</strong><br>
                        <em>"{item.source_b}"</em>
                    </div>
                    <div>
                        <strong>Why Flagged:</strong> {item.reason}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with tab_compat:
        compatibles = [r for r in results if r.classification == "compatible"]
        if not compatibles:
            st.info("No matching compatible claims found.")
        else:
            for idx, item in enumerate(compatibles, 1):
                st.markdown(f"""
                <div class="compatible-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <span style="color: #2e7d32; font-weight: 700; font-size: 1.05rem;">
                            ✅ COMPATIBLE FACT #{idx}
                        </span>
                        <span class="badge-consistent">Status: {item.status}</span>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong>Topic:</strong> <code>{item.topic.replace('_', ' ').title()}</code> &nbsp;|&nbsp; 
                        <strong>Confidence:</strong> {item.confidence * 100:.1f}%
                    </div>
                    <div style="background-color: #ffffff; padding: 10px; border-radius: 6px; margin-bottom: 8px; border: 1px solid #e8f5e9;">
                        <strong>Source A:</strong> <em>"{item.source_a}"</em>
                    </div>
                    <div style="background-color: #ffffff; padding: 10px; border-radius: 6px; margin-bottom: 8px; border: 1px solid #e8f5e9;">
                        <strong>Source B:</strong> <em>"{item.source_b}"</em>
                    </div>
                    <div>
                        <strong>Validation:</strong> {item.reason}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with tab_claims:
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            st.markdown(f"#### Claims in {label_a} ({len(claims_a)})")
            for ca in claims_a:
                st.json(ca.model_dump())
        with c_col2:
            st.markdown(f"#### Claims in {label_b} ({len(claims_b)})")
            for cb in claims_b:
                st.json(cb.model_dump())

    with tab_history:
        runs = db.list_runs(limit=10)
        if runs:
            st.dataframe(runs, use_container_width=True)
        else:
            st.write("No audit history found yet.")
