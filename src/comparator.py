"""Claim Comparison & Decision Logic Module.

Implements Comparison Decision Flow, Pydantic Result Model, Prompts, and
Responsible AI phrasing according to PDF 03 specifications.
"""

from typing import Dict, Any, Optional, Literal
from enum import Enum
import json
import re
from pydantic import BaseModel, Field, field_validator, ValidationError
from .claims import Claim


class ClassificationType(str, Enum):
    CONTRADICTION = "contradiction"
    COMPATIBLE = "compatible"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class ComparisonResult(BaseModel):
    """Pydantic model for contradiction comparison output.

    Strictly matches PDF 03 & PDF 04 schemas.
    """
    topic: str = Field(..., description="Subject or attribute under comparison")
    classification: Literal["contradiction", "compatible", "insufficient_information"] = Field(
        ..., description="Contradiction decision classification"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model-generated estimate for human review prioritization"
    )
    reason: str = Field(..., description="Objective explanation using 'potential contradiction' phrasing")
    claim_a: Any = Field(..., description="Claim A identifier, summary, or details")
    claim_b: Any = Field(..., description="Claim B identifier, summary, or details")
    source_a: str = Field(..., description="Exact source sentence from Document A")
    source_b: str = Field(..., description="Exact source sentence from Document B")
    status: str = Field(default="Requires human verification", description="Actionable status banner")

    @field_validator("reason")
    @classmethod
    def sanitize_responsible_ai(cls, v: str) -> str:
        """Responsible AI check: Prohibits defamatory or judicial accusations."""
        prohibited = ["liar", "fraudster", "dishonest", "fraud", "scammer", "fake document"]
        v_lower = v.lower()
        for word in prohibited:
            if word in v_lower:
                # Neutralize defamatory language automatically
                v = re.sub(re.escape(word), "conflicting data point", v, flags=re.IGNORECASE)
        return v


COMPARISON_SYSTEM_PROMPT = """SYSTEM: You are an objective factual comparison engine.
RULES:
1. Compare the two supplied claims only.
2. Do not use outside knowledge.
3. Do not invent missing facts.
4. Do not call a source false, a liar, or fraudulent.
5. Use "potential contradiction" in the explanation if values conflict.
6. Return valid JSON only.

CLASSIFICATION OPTIONS:
- "contradiction": The facts directly conflict on the same attribute.
- "compatible": The facts agree, describe the same reality, or are consistent.
- "insufficient_information": One or both claims lack enough factual detail to confirm consistency or conflict.

OUTPUT JSON FORMAT:
{
  "classification": "contradiction | compatible | insufficient_information",
  "confidence": 0.85,
  "reason": "The reported employment periods differ (January 2024 to December 2024 vs June 2023 to March 2025). This represents a potential contradiction requiring human verification.",
  "claim_a": "A-01",
  "claim_b": "B-01"
}
"""


def build_comparison_prompt(claim_a: Claim, claim_b: Claim) -> str:
    """Builds prompt to compare two aligned claims."""
    return f"""{COMPARISON_SYSTEM_PROMPT}

CLAIM A (from {claim_a.source}):
Subject: {claim_a.subject}
Attribute: {claim_a.attribute}
Value: {json.dumps(claim_a.value) if isinstance(claim_a.value, (dict, list)) else claim_a.value}
Source Text: "{claim_a.source_text}"

CLAIM B (from {claim_b.source}):
Subject: {claim_b.subject}
Attribute: {claim_b.attribute}
Value: {json.dumps(claim_b.value) if isinstance(claim_b.value, (dict, list)) else claim_b.value}
Source Text: "{claim_b.source_text}"

Compare these two claims according to the decision flow. Return JSON only:"""


def parse_and_validate_comparison(
    raw_json_text: str,
    claim_a: Claim,
    claim_b: Claim,
    topic: str
) -> ComparisonResult:
    """Parses model comparison JSON, recovers markdown fences, and builds validated ComparisonResult."""
    clean_str = raw_json_text.strip()
    if clean_str.startswith("```"):
        clean_str = re.sub(r"^```(?:json)?\s*", "", clean_str)
        clean_str = re.sub(r"\s*```$", "", clean_str)

    data = json.loads(clean_str)

    # Normalize fields
    classification = str(data.get("classification", "insufficient_information")).lower()
    if classification not in ["contradiction", "compatible", "insufficient_information"]:
        if "contradict" in classification:
            classification = "contradiction"
        elif "compat" in classification:
            classification = "compatible"
        else:
            classification = "insufficient_information"

    confidence = float(data.get("confidence", 0.70))
    confidence = max(0.0, min(1.0, confidence))

    reason = str(data.get("reason", "Comparison completed based on reported values."))

    return ComparisonResult(
        topic=topic,
        classification=classification,
        confidence=confidence,
        reason=reason,
        claim_a=data.get("claim_a", claim_a.to_summary()),
        claim_b=data.get("claim_b", claim_b.to_summary()),
        source_a=claim_a.source_text,
        source_b=claim_b.source_text,
        status="Requires human verification" if classification == "contradiction" else "Consistent"
    )


def compare_claims_rule_based(claim_a: Claim, claim_b: Claim, topic: str) -> ComparisonResult:
    """Deterministic comparison engine following PDF 03 Decision Flow:

    Decision Flow:
    1. Are the claims about the same topic? (Handled before entry or checked here)
    2. Are both claims factual enough to compare?
       NO -> insufficient_information
    3. Do values conflict?
       YES -> potential contradiction
       NO  -> compatible
    """
    val_a = claim_a.value
    val_b = claim_b.value

    # Check for empty / insufficient info
    if val_a is None or val_b is None or str(val_a).strip() == "" or str(val_b).strip() == "":
        return ComparisonResult(
            topic=topic,
            classification="insufficient_information",
            confidence=0.50,
            reason="One or both claims lack factual value to complete comparison.",
            claim_a=claim_a.to_summary(),
            claim_b=claim_b.to_summary(),
            source_a=claim_a.source_text,
            source_b=claim_b.source_text,
            status="Insufficient data"
        )

    # Dictionary comparison (e.g. date ranges)
    if isinstance(val_a, dict) and isinstance(val_b, dict):
        diffs = []
        for k in set(val_a.keys()).union(set(val_b.keys())):
            if val_a.get(k) != val_b.get(k):
                diffs.append(f"{k} differs ({val_a.get(k)} vs {val_b.get(k)})")

        if diffs:
            return ComparisonResult(
                topic=topic,
                classification="contradiction",
                confidence=0.94,
                reason=f"The reported {topic.replace('_', ' ')} values conflict: {', '.join(diffs)}. Potential contradiction requiring human verification.",
                claim_a=claim_a.to_summary(),
                claim_b=claim_b.to_summary(),
                source_a=claim_a.source_text,
                source_b=claim_b.source_text,
                status="Requires human verification"
            )
        else:
            return ComparisonResult(
                topic=topic,
                classification="compatible",
                confidence=0.95,
                reason=f"The reported {topic.replace('_', ' ')} values match completely.",
                claim_a=claim_a.to_summary(),
                claim_b=claim_b.to_summary(),
                source_a=claim_a.source_text,
                source_b=claim_b.source_text,
                status="Consistent"
            )

    # Direct value or string comparison
    norm_a = str(val_a).strip().lower()
    norm_b = str(val_b).strip().lower()

    if norm_a == norm_b:
        return ComparisonResult(
            topic=topic,
            classification="compatible",
            confidence=0.95,
            reason=f"Both documents report the exact same value for {topic.replace('_', ' ')}: '{val_a}'.",
            claim_a=claim_a.to_summary(),
            claim_b=claim_b.to_summary(),
            source_a=claim_a.source_text,
            source_b=claim_b.source_text,
            status="Consistent"
        )
    else:
        # Check numeric equivalence e.g. 50000 vs 50,000
        num_clean_a = re.sub(r"[^\d\.]", "", norm_a)
        num_clean_b = re.sub(r"[^\d\.]", "", norm_b)
        if num_clean_a and num_clean_b and num_clean_a == num_clean_b:
            return ComparisonResult(
                topic=topic,
                classification="compatible",
                confidence=0.92,
                reason=f"Values represent identical numerical quantities despite formatting differences: '{val_a}' vs '{val_b}'.",
                claim_a=claim_a.to_summary(),
                claim_b=claim_b.to_summary(),
                source_a=claim_a.source_text,
                source_b=claim_b.source_text,
                status="Consistent"
            )

        return ComparisonResult(
            topic=topic,
            classification="contradiction",
            confidence=0.91,
            reason=f"The reported {topic.replace('_', ' ')} values conflict: '{val_a}' vs '{val_b}'. Potential contradiction requiring human verification.",
            claim_a=claim_a.to_summary(),
            claim_b=claim_b.to_summary(),
            source_a=claim_a.source_text,
            source_b=claim_b.source_text,
            status="Requires human verification"
        )
