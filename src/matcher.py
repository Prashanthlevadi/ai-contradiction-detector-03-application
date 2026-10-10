"""Claim Alignment and Candidate Matching Module.

Implements topic-based claim alignment to avoid blind all-to-all quadratic
comparison, matching PDF 03 specifications.
"""

from typing import List, Dict, Any, Tuple
import re
from difflib import SequenceMatcher
from .claims import Claim


def normalize_topic_string(text: str) -> str:
    """Normalizes subject/attribute tokens for robust semantic matching."""
    s = text.lower().replace("_", " ").replace("-", " ")
    return re.sub(r"[^\w\s]", "", s).strip()


def calculate_similarity(s1: str, s2: str) -> float:
    """Calculates Levenshtein-based sequence similarity between two token strings."""
    return SequenceMatcher(None, normalize_topic_string(s1), normalize_topic_string(s2)).ratio()


def is_compatible_topic(claim_a: Claim, claim_b: Claim) -> Tuple[bool, float, str]:
    """Determines whether two claims refer to the same underlying fact/topic.

    Returns:
        Tuple of (should_align: bool, match_score: float, topic_label: str)
    """
    attr_a = normalize_topic_string(claim_a.attribute)
    attr_b = normalize_topic_string(claim_b.attribute)

    subj_a = normalize_topic_string(claim_a.subject)
    subj_b = normalize_topic_string(claim_b.subject)

    # 1. Exact attribute match
    if attr_a == attr_b:
        # Check subject compatibility if attributes match
        subj_sim = calculate_similarity(subj_a, subj_b)
        # Even if subjects differ slightly (e.g. 'Project' vs 'Project Allocation'), align if related
        if subj_sim > 0.4 or "project" in subj_a and "project" in subj_b:
            return True, 0.95, claim_a.attribute
        elif subj_sim > 0.2:
            return True, 0.80, claim_a.attribute

    # 2. Semantic synonyms for common attributes
    synonym_groups = [
        {"employment_period", "employment_dates", "joining_date", "dates", "tenure"},
        {"project_budget", "budget", "project_allocation", "allocation", "cost"},
        {"current_location", "location", "city", "residence", "current_residence"},
        {"degree", "education", "qualification", "academic_degree"},
        {"degree_status", "graduation_status", "status", "completion_status"},
        {"job_role", "role", "position", "title", "designation"}
    ]

    for group in synonym_groups:
        cleaned_group = {normalize_topic_string(item) for item in group}
        if attr_a in cleaned_group and attr_b in cleaned_group:
            return True, 0.90, list(group)[0]

    # 3. Fuzzy attribute similarity
    attr_sim = calculate_similarity(attr_a, attr_b)
    if attr_sim >= 0.75:
        return True, attr_sim, claim_a.attribute

    return False, 0.0, "unaligned"


def find_candidate_pairs(claims_a: List[Claim], claims_b: List[Claim]) -> List[Dict[str, Any]]:
    """Aligns claims from Document A and Document B sharing underlying topics.

    Filters out irrelevant pairs (e.g. Employment Dates vs CGPA),
    preventing quadratic LLM calls.

    Returns:
        List of dicts: {"a": Claim, "b": Claim, "topic": str, "score": float}
    """
    candidate_pairs: List[Dict[str, Any]] = []

    for ca in claims_a:
        for cb in claims_b:
            should_align, score, topic = is_compatible_topic(ca, cb)
            if should_align:
                candidate_pairs.append({
                    "a": ca,
                    "b": cb,
                    "topic": topic,
                    "similarity": round(score, 3)
                })

    return candidate_pairs
