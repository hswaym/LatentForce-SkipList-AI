CONFIDENCE_WEIGHTS = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.3,
}

TYPE_MULTIPLIERS = {
    "duplicate": 2.0,
    "dead_code": 1.0,
}


def compute_priority_score(lines: int, confidence: str, finding_type: str) -> int:
    """Compute deterministic priority score for a finding based on line count, confidence, and type."""
    conf_weight = CONFIDENCE_WEIGHTS.get(confidence, 1.0)
    type_mult = TYPE_MULTIPLIERS.get(finding_type, 1.0)
    return round(lines * conf_weight * type_mult)
