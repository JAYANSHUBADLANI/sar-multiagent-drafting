import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from case_formatter import format_case_as_text, load_case
from evaluate import find_account_numbers, score_coverage, score_hallucination
from red_flags_reference import RED_FLAGS

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def test_case_file_has_expected_structure():
    case = load_case(DATA_DIR / "case_246.json")
    assert case["ring_id"] == 246
    assert case["typology"] == "FAN-OUT"
    assert case["n_transactions"] == len(case["transactions"])
    assert len(case["accounts"]) == case["n_accounts"]


def test_case_formatter_includes_every_transaction():
    case = load_case(DATA_DIR / "case_246.json")
    text = format_case_as_text(case)
    for t in case["transactions"]:
        assert t["from_account"] in text
        assert t["to_account"] in text


def test_find_account_numbers_matches_known_pattern():
    text = "Account 8045F4500 sent funds to 80E5DE3D0 and mentioned ABC123 which is not an account."
    found = find_account_numbers(text)
    assert "8045F4500" in found
    assert "80E5DE3D0" in found
    assert "ABC123" not in found


def test_score_hallucination_flags_unknown_account():
    known = {"8045F4500", "80E5DE3D0"}
    narrative = "Funds moved from 8045F4500 to 80E5DE3D0 and then to 809999999."
    result = score_hallucination(narrative, known)
    assert "809999999" in result["accounts_hallucinated"]
    assert result["n_hallucinated"] == 1


def test_score_hallucination_clean_narrative_has_zero():
    known = {"8045F4500", "80E5DE3D0"}
    narrative = "Funds moved from 8045F4500 to 80E5DE3D0."
    result = score_hallucination(narrative, known)
    assert result["n_hallucinated"] == 0


def test_score_coverage_detects_cited_flag():
    narrative = (
        "Account 8045F4500 at bank 11128 sent funds to 13 different accounts "
        "across 12 different banks in a dispersal pattern."
    )
    result = score_coverage(narrative)
    fan_out = next(f for f in result["per_flag"] if f["key"] == "single_source_fan_out")
    assert fan_out["adequately_cited"]


def test_score_coverage_flags_missing_citation():
    narrative = "This case shows suspicious activity of some kind."
    result = score_coverage(narrative)
    assert result["n_red_flags_adequately_cited"] == 0
    assert result["coverage_pct"] == 0.0


def test_red_flags_reference_all_have_citation_requirements():
    for rf in RED_FLAGS:
        assert len(rf["requires_citation_of"]) > 0
        assert "key" in rf and "description" in rf


def test_comparison_results_file_has_both_approaches():
    results_path = ROOT / "results" / "comparison.json"
    with open(results_path) as f:
        results = json.load(f)
    assert "baseline" in results
    assert "multiagent" in results
    assert results["baseline"]["evaluation"]["hallucination"]["n_hallucinated"] == 0
    assert results["multiagent"]["evaluation"]["hallucination"]["n_hallucinated"] == 0
