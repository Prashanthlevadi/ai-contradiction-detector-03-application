"""Text Cleaning and Normalization Module.

Implements text cleanup and line normalization according to PDF 02 specifications.
"""

import re


def clean_text(text: str) -> str:
    """Normalize extracted document text.

    Strips whitespace per line, removes empty lines, and joins remaining content.

    Args:
        text: Raw text string from extraction or user input.

    Returns:
        Cleaned, normalized multi-line string.
    """
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def normalize_whitespace(text: str) -> str:
    """Collapses multiple horizontal spaces and tabs into a single space.

    Args:
        text: Input string.

    Returns:
        String with normalized horizontal spaces.
    """
    if not text:
        return ""
    cleaned = clean_text(text)
    return re.sub(r"[ \t]+", " ", cleaned)
