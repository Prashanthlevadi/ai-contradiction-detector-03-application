"""Error Handling and Diagnostic Flow Module.

Implements structured exception taxonomy and user-facing diagnostic messages
according to PDF 04 Step 8.
"""

from typing import Dict, Any, Optional
from .llm_client import redact_secrets


class ContradictionAppError(Exception):
    """Base application exception."""
    def __init__(self, message: str, user_friendly_message: Optional[str] = None):
        super().__init__(message)
        self.user_friendly_message = user_friendly_message or message


class MissingInputError(ContradictionAppError):
    """Raised when one or both documents are missing."""
    pass


class UnreadablePDFError(ContradictionAppError):
    """Raised when PDF bytes cannot be parsed or are corrupted."""
    pass


class ZeroTextOCRError(ContradictionAppError):
    """Raised when a PDF contains 0 extractable characters (scanned/image-only)."""
    pass


class ModelValidationError(ContradictionAppError):
    """Raised when AI output does not match expected Pydantic schema."""
    pass


class SecureAPIError(ContradictionAppError):
    """Raised when external API call fails, strictly redacting secret tokens."""
    def __init__(self, raw_exception: Exception):
        safe_text = redact_secrets(str(raw_exception))
        user_msg = (
            f"External AI Provider API error: {safe_text}. "
            "Please check API keys, quota, or network connectivity. Secrets have been safely redacted."
        )
        super().__init__(safe_text, user_friendly_message=user_msg)


def diagnose_inputs(text_a: str, text_b: str, diag_a: Optional[Dict[str, Any]] = None, diag_b: Optional[Dict[str, Any]] = None):
    """Validates inputs before entering AI pipeline according to PDF 04 Error Flow."""
    if not text_a or not text_a.strip():
        if diag_a and diag_a.get("is_likely_scanned"):
            raise ZeroTextOCRError(
                "Source A is an image-only or scanned PDF. PyMuPDF extracted 0 text characters. "
                "An OCR engine is required for scanned documents."
            )
        raise MissingInputError("Source A document content is missing. Please provide Source A.")

    if not text_b or not text_b.strip():
        if diag_b and diag_b.get("is_likely_scanned"):
            raise ZeroTextOCRError(
                "Source B is an image-only or scanned PDF. PyMuPDF extracted 0 text characters. "
                "An OCR engine is required for scanned documents."
            )
        raise MissingInputError("Source B document content is missing. Please provide Source B.")
