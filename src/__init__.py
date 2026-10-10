"""AI Contradiction Detector - Application Module (Stage 3)."""

from .pdf_reader import extract_text, inspect_pdf, PDFExtractionError
from .cleaner import clean_text, normalize_whitespace
from .claims import Claim, parse_and_validate_claims, extract_claims_rule_based
from .matcher import find_candidate_pairs, is_compatible_topic
from .comparator import ComparisonResult, compare_claims_rule_based, parse_and_validate_comparison
from .pipeline import ContradictionPipeline
from .llm_client import LLMClient, redact_secrets
from .errors import (
    ContradictionAppError,
    MissingInputError,
    UnreadablePDFError,
    ZeroTextOCRError,
    ModelValidationError,
    SecureAPIError,
    diagnose_inputs,
)
from .history import HistoryDB

__all__ = [
    "extract_text",
    "inspect_pdf",
    "PDFExtractionError",
    "clean_text",
    "normalize_whitespace",
    "Claim",
    "parse_and_validate_claims",
    "extract_claims_rule_based",
    "find_candidate_pairs",
    "is_compatible_topic",
    "ComparisonResult",
    "compare_claims_rule_based",
    "parse_and_validate_comparison",
    "ContradictionPipeline",
    "LLMClient",
    "redact_secrets",
    "ContradictionAppError",
    "MissingInputError",
    "UnreadablePDFError",
    "ZeroTextOCRError",
    "ModelValidationError",
    "SecureAPIError",
    "diagnose_inputs",
    "HistoryDB",
]
