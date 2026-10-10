"""Automated Test Suite for Stage 03 Application.

Verifies:
- End-to-end execution of full pipeline.
- Metric summary calculation (PDF 04 Step 7).
- Error flows (missing input, zero text / OCR limitation).
- Secret redaction in error messages (PDF 04 Step 8).
- SQLite history audit recording (PDF 04 Step 9).
"""

import os
import sys
import pytest

STAGE3_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if STAGE3_DIR not in sys.path:
    sys.path.insert(0, STAGE3_DIR)

from src.pipeline import ContradictionPipeline
from src.errors import diagnose_inputs, MissingInputError, ZeroTextOCRError
from src.llm_client import redact_secrets
from src.history import HistoryDB


def test_pipeline_metrics_summary():
    pipe = ContradictionPipeline()
    text_a = "Company: ABC Technologies\nEmployment Period: January 2024 to December 2024\nProject Budget: $50,000\n"
    text_b = "Company: ABC Technologies\nEmployment Dates: June 2023 to March 2025\nProject Budget: $50,000\n"

    out = pipe.process_texts(text_a, text_b)
    m = out["metrics"]

    assert m["sources_processed"] == 2
    assert m["claims_analyzed"] >= 4
    assert m["contradictions"] >= 1  # Employment period
    assert m["compatible"] >= 1     # Project budget


def test_missing_input_error():
    with pytest.raises(MissingInputError):
        diagnose_inputs("", "Valid content")

    with pytest.raises(MissingInputError):
        diagnose_inputs("Valid content", "   ")


def test_zero_text_ocr_error():
    diag_scanned = {"is_likely_scanned": True, "char_count": 0, "page_count": 1}
    with pytest.raises(ZeroTextOCRError, match="OCR engine is required"):
        diagnose_inputs("", "Valid content", diag_a=diag_scanned)


def test_secret_redaction():
    fake_openai = "Error connecting to OpenAI with key sk-1234567890abcdef123456"
    fake_gemini = "Gemini key AIzaSyD1234567890abcdef123456 failed quota"
    fake_github = "Token gho_1234567890abcdef1234567890abcdef123456 is invalid"

    redacted_openai = redact_secrets(fake_openai)
    redacted_gemini = redact_secrets(fake_gemini)
    redacted_github = redact_secrets(fake_github)

    assert "sk-1234567890abcdef123456" not in redacted_openai
    assert "[REDACTED_OPENAI_KEY]" in redacted_openai

    assert "AIzaSyD1234567890abcdef123456" not in redacted_gemini
    assert "[REDACTED_GEMINI_KEY]" in redacted_gemini

    assert "gho_1234567890abcdef1234567890abcdef123456" not in redacted_github
    assert "[REDACTED_GITHUB_KEY]" in redacted_github


def test_sqlite_history_audit(tmp_path):
    db_file = os.path.join(tmp_path, "test_hist.sqlite")
    hdb = HistoryDB(db_path=db_file)

    metrics = {"contradictions": 2, "compatible": 1, "insufficient": 0, "claims_analyzed": 5}
    run_id = hdb.record_run("DocA.pdf", "DocB.pdf", metrics, [])
    assert run_id >= 1

    runs = hdb.list_runs()
    assert len(runs) == 1
    assert runs[0]["source_a_label"] == "DocA.pdf"
    assert runs[0]["contradictions_count"] == 2
