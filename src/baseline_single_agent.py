"""
A single agent baseline: one model call, same case data, asked to produce
a complete SAR narrative directly, no retrieval, analysis, drafting, or
critic separation. This is the comparison point the multi-agent pipeline
has to actually beat, not a deliberately weak strawman: it gets the same
model, the same case text, and an instruction that names the same things a
SAR narrative needs, just asked to do the whole job in one pass.
"""

from __future__ import annotations

from agents import MODEL_NAME, get_llm


def run_single_agent(case_text: str) -> str:
    llm = get_llm()
    prompt = f"""You are a financial crimes compliance analyst. Below is the raw
transaction and account data for a flagged case.

{case_text}

Task: write the narrative section of a Suspicious Activity Report (SAR) for
this case. Identify the red flags this evidence supports (patterns like fund
dispersal to many unrelated counterparties, unusual currency or
jurisdiction spread, irregular or inconsistent transaction amounts,
unusually high transaction velocity, outlier large transactions embedded
among smaller ones, and absence of an apparent legitimate business
purpose), citing specific account numbers, dates, and dollar amounts for
each. Cover what happened, who was involved, when, how much, and why it is
suspicious. Be precise and factual, do not speculate beyond what the
evidence supports. Write only the narrative text."""
    result = llm.invoke(prompt)
    return result.content
