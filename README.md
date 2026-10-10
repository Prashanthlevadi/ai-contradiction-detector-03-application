# Stage 03: Application Build, UI, Evidence Display & Error Flows
**AI Contradiction Detector — 1-Week Practical AI/NLP Mini-Project**  
*Reference: PDF 04 Official Student Build Guide*

---

## 1. Overview
The Stage 03 Application delivers the complete interactive Streamlit web application. It connects all pipeline modules—from document parsing and text cleaning to claim extraction, topic alignment, pairwise fact comparison, and SQLite audit logging—with rich visual evidence cards and summary metric dashboards.

---

## 2. Features

- **Dual-Source Input:** Upload PDF files, choose synthetic classroom demonstration scenarios, or paste raw text.
- **Explainable Evidence Cards:** Every potential contradiction displays verbatim source quotes from both documents side-by-side.
- **Summary Metrics:** Live KPIs tracking contradictions, compatible facts, insufficient data, claims analyzed, and sources processed.
- **Responsible AI Compliance:**
  - Neutral non-accusatory language.
  - "Potential Contradiction" framing.
  - "Requires human verification" status tag.
  - Explicit notification that confidence scores are model estimation heuristics.
- **Comprehensive Error Flow:** Graceful handling for missing inputs, unreadable PDFs, OCR limitations (scanned PDFs), and automatic secret redaction.
- **SQLite Audit History:** Saves past verification sessions locally for review.

---

## 3. How to Run

1. **Activate Virtual Environment & Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Key (Optional):**
   ```bash
   cp .env.example .env
   # Add GEMINI_API_KEY or OPENAI_API_KEY
   # Note: The application also supports the zero-token offline deterministic engine out of the box!
   ```

3. **Launch the Application:**
   ```bash
   streamlit run app.py
   ```
   Open `http://localhost:8501` in your browser.

---

## 4. Automated Testing

Run the automated test suite:
```bash
python -m pytest tests/test_stage3.py -v
```

Run the Day 4–5 Definition of Done verification:
```bash
python verify_stage3.py
```

---

## 5. Day 4–5 Definition of Done Audit

| Checkpoint | Pass Criteria | Result | Evidence |
| :--- | :--- | :--- | :--- |
| **Complete Analysis** | User can complete entire analysis from UI | ✅ PASS | One-click synthetic demo & upload flows |
| **Both Outcomes Display** | Contradiction and compatible examples displayed | ✅ PASS | Both cards rendered with color-coded badges |
| **Source Evidence** | Every contradiction includes source evidence | ✅ PASS | Verbatim quotes from Doc A & Doc B verified |
| **Graceful Errors** | Empty input and API failures handled safely | ✅ PASS | User-friendly warnings and key redaction |
| **Demo Ready** | Operable without editing code during demo | ✅ PASS | Fully interactive UI with built-in presets |
