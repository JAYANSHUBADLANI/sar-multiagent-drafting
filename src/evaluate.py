"""
Scores a generated SAR narrative against the ground truth red flags
reference (red_flags_reference.py, worked out by reading the raw data
directly, not by asking a model first). Two things are measured:

Coverage: for each red flag this case's evidence actually supports, does
the narrative name it and cite enough of the specific evidence (account
numbers, dates, dollar amounts) that a reviewer could verify the claim
against the source data, rather than a vague, uncited assertion.

Hallucination: does the narrative mention any account number that is not
actually one of the 14 real accounts in this case. A narrative that reads
well but invents an account number is a worse compliance document than
one that is less polished but only states what the evidence shows.
"""

from __future__ import annotations

import re

from red_flags_reference import RED_FLAGS


def score_coverage(narrative: str) -> dict:
    narrative_lower = narrative.lower()
    per_flag = []
    for rf in RED_FLAGS:
        hits = [c for c in rf["requires_citation_of"] if c.lower() in narrative_lower]
        mentioned = rf["key"].replace("_", " ").split()[0] in narrative_lower or len(hits) > 0
        cited = len(hits) >= max(1, len(rf["requires_citation_of"]) // 2)
        per_flag.append({
            "key": rf["key"],
            "citations_found": hits,
            "n_citations_required": len(rf["requires_citation_of"]),
            "adequately_cited": cited,
        })
    n_cited = sum(1 for f in per_flag if f["adequately_cited"])
    return {
        "per_flag": per_flag,
        "n_red_flags_total": len(RED_FLAGS),
        "n_red_flags_adequately_cited": n_cited,
        "coverage_pct": n_cited / len(RED_FLAGS),
    }


def find_account_numbers(text: str) -> set:
    # accounts in this dataset look like 8045F4500, hex-ish alphanumeric, 9 chars
    return set(re.findall(r"\b8[0-9A-F]{8}\b", text.upper()))


def score_hallucination(narrative: str, known_accounts: set) -> dict:
    mentioned = find_account_numbers(narrative)
    hallucinated = mentioned - known_accounts
    return {
        "accounts_mentioned": sorted(mentioned),
        "accounts_hallucinated": sorted(hallucinated),
        "n_hallucinated": len(hallucinated),
    }


def evaluate_narrative(narrative: str, known_accounts: set) -> dict:
    coverage = score_coverage(narrative)
    hallucination = score_hallucination(narrative, known_accounts)
    return {
        "coverage": coverage,
        "hallucination": hallucination,
        "narrative_length_chars": len(narrative),
    }
