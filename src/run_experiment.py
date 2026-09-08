"""
Runs both the multi-agent pipeline and the single-agent baseline on the
same real flagged case, scores both against the ground truth red flag
reference, and saves everything so the comparison is inspectable rather
than just a headline number.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from agents import run_multiagent
from baseline_single_agent import run_single_agent
from case_formatter import format_case_as_text, load_case
from evaluate import evaluate_narrative

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    case = load_case(DATA_DIR / "case_246.json")
    case_text = format_case_as_text(case)
    known_accounts = {a["account"] for a in case["accounts"]}

    print("running single agent baseline")
    t0 = time.time()
    baseline_narrative = run_single_agent(case_text)
    baseline_time = time.time() - t0
    print(f"baseline done in {baseline_time:.1f}s")

    print("running multi agent pipeline")
    t0 = time.time()
    final_state = run_multiagent(case_text)
    multiagent_time = time.time() - t0
    print(f"multi agent done in {multiagent_time:.1f}s, "
          f"{final_state['revision_round']} critic round(s)")

    multiagent_narrative = final_state["final_narrative"]

    baseline_eval = evaluate_narrative(baseline_narrative, known_accounts)
    multiagent_eval = evaluate_narrative(multiagent_narrative, known_accounts)

    print(f"\nbaseline coverage: {baseline_eval['coverage']['n_red_flags_adequately_cited']}/"
          f"{baseline_eval['coverage']['n_red_flags_total']} red flags adequately cited, "
          f"{baseline_eval['hallucination']['n_hallucinated']} hallucinated accounts")
    print(f"multi-agent coverage: {multiagent_eval['coverage']['n_red_flags_adequately_cited']}/"
          f"{multiagent_eval['coverage']['n_red_flags_total']} red flags adequately cited, "
          f"{multiagent_eval['hallucination']['n_hallucinated']} hallucinated accounts")

    output = {
        "case_id": case["ring_id"],
        "baseline": {
            "narrative": baseline_narrative,
            "runtime_seconds": baseline_time,
            "evaluation": baseline_eval,
        },
        "multiagent": {
            "narrative": multiagent_narrative,
            "runtime_seconds": multiagent_time,
            "critic_rounds": final_state["revision_round"],
            "intermediate": {
                "retrieved_evidence": final_state["retrieved_evidence"],
                "red_flags_identified": final_state["red_flags_identified"],
            },
            "evaluation": multiagent_eval,
        },
    }
    with open(RESULTS_DIR / "comparison.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nfull results written to {RESULTS_DIR / 'comparison.json'}")


if __name__ == "__main__":
    main()
