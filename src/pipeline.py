"""End-to-End Contradiction Pipeline Architecture.

Implements the multi-stage pipeline defined in PDF 03:
1. Source extraction
2. Text cleaning
3. Claim extraction
4. Topic alignment
5. Comparison & classification
6. Result aggregation
"""

from typing import List, Dict, Any, Tuple
from .pdf_reader import extract_text
from .cleaner import clean_text
from .claims import Claim, extract_claims_rule_based
from .matcher import find_candidate_pairs
from .comparator import ComparisonResult, compare_claims_rule_based


class ContradictionPipeline:
    """Orchestrates the modular multi-stage contradiction detection workflow."""

    def __init__(self, use_rule_engine: bool = True):
        self.use_rule_engine = use_rule_engine

    def process_texts(
        self,
        text_a: str,
        text_b: str,
        label_a: str = "Document A",
        label_b: str = "Document B"
    ) -> Dict[str, Any]:
        """Runs the entire pipeline from raw text inputs."""
        # 1. Clean and normalize
        clean_a = clean_text(text_a)
        clean_b = clean_text(text_b)

        # 2. Extract claims
        claims_a = extract_claims_rule_based(clean_a, source_label=label_a)
        claims_b = extract_claims_rule_based(clean_b, source_label=label_b)

        # 3. Align candidate claims
        candidate_pairs = find_candidate_pairs(claims_a, claims_b)

        # 4. Compare aligned claims
        results: List[ComparisonResult] = []
        for pair in candidate_pairs:
            comp = compare_claims_rule_based(pair["a"], pair["b"], topic=pair["topic"])
            results.append(comp)

        # 5. Compute summary metrics
        contradictions = sum(1 for r in results if r.classification == "contradiction")
        compatibles = sum(1 for r in results if r.classification == "compatible")
        insufficient = sum(1 for r in results if r.classification == "insufficient_information")

        return {
            "claims_a": claims_a,
            "claims_b": claims_b,
            "candidate_pairs_count": len(candidate_pairs),
            "results": results,
            "metrics": {
                "contradictions": contradictions,
                "compatible": compatibles,
                "insufficient": insufficient,
                "claims_analyzed": len(claims_a) + len(claims_b),
                "sources_processed": 2
            }
        }

    def process_bytes(
        self,
        bytes_a: bytes,
        bytes_b: bytes,
        label_a: str = "Document A",
        label_b: str = "Document B"
    ) -> Dict[str, Any]:
        """Runs the entire pipeline from PDF raw byte streams."""
        text_a = extract_text(bytes_a)
        text_b = extract_text(bytes_b)
        return self.process_texts(text_a, text_b, label_a, label_b)
