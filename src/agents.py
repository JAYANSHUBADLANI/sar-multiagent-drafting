"""
The four agent LangGraph pipeline: retrieval, analysis, drafting, critic.

Kept deliberately to plain text generation between nodes rather than forced
JSON tool calling at every step: a 14B local model is meaningfully less
reliable at strict structured output than a frontier API model, and the
thing actually being tested here, whether specialization and a critique
step improve a SAR narrative over one shot generation, does not depend on
inter agent messages being machine parseable JSON, only on the final
narrative being better. The critic node is the one place structure matters,
a clear APPROVED or REVISE verdict, and that is enforced by checking for
those literal tokens rather than trusting free form JSON from a small model.
"""

from __future__ import annotations

from typing import TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph

from red_flags_reference import RED_FLAGS

MODEL_NAME = "qwen2.5:14b"
MAX_CRITIC_ROUNDS = 2


def get_llm(temperature: float = 0.2) -> ChatOllama:
    return ChatOllama(model=MODEL_NAME, temperature=temperature)


class SARState(TypedDict):
    case_text: str
    retrieved_evidence: str
    red_flags_identified: str
    draft_narrative: str
    critic_feedback: str
    critic_verdict: str
    revision_round: int
    final_narrative: str


def retrieval_node(state: SARState) -> dict:
    llm = get_llm()
    prompt = f"""You are a financial crimes compliance analyst's retrieval assistant.
Below is the raw transaction and account data for a flagged case.

{state['case_text']}

Task: extract and organize the specific facts a SAR narrative would need:
exact account numbers, bank names or IDs, exact dates and times, exact
dollar amounts and currencies, and the overall shape of the fund flow
(who sent to whom, in what order). Do not analyze or draw conclusions yet,
only organize the facts precisely, quoting exact numbers and dates as they
appear above. Do not omit any transaction."""
    result = llm.invoke(prompt)
    return {"retrieved_evidence": result.content}


def analysis_node(state: SARState) -> dict:
    llm = get_llm()
    prompt = f"""You are a financial crimes compliance analyst. Below is organized
evidence for a flagged case.

{state['retrieved_evidence']}

Task: identify every red flag this evidence actually supports, the kind of
indicators used in Suspicious Activity Report filings: patterns like fund
dispersal to many unrelated counterparties, unusual currency or
jurisdiction spread, irregular or inconsistent transaction amounts,
unusually high transaction velocity, outlier large transactions embedded
among smaller ones, and absence of an apparent legitimate business
purpose. For each red flag you identify, state it clearly and cite the
specific account numbers, dates, and dollar amounts from the evidence that
support it. Do not claim a red flag you cannot cite specific evidence for.
Do not invent facts not present in the evidence above."""
    result = llm.invoke(prompt)
    return {"red_flags_identified": result.content}


def drafting_node(state: SARState) -> dict:
    llm = get_llm()
    revision_note = ""
    if state.get("critic_feedback"):
        revision_note = f"""
A compliance reviewer previously sent this narrative back with the following
feedback. Address every point:
{state['critic_feedback']}

Previous draft:
{state.get('draft_narrative', '')}
"""
    prompt = f"""You are drafting the narrative section of a Suspicious Activity
Report (SAR). Below are the identified red flags and their supporting
evidence.

{state['red_flags_identified']}
{revision_note}

Task: write a SAR narrative in the standard structure a compliance officer
would file: what happened, who was involved (exact account numbers and
banks), when (exact dates), how much (exact amounts and currencies), why it
is suspicious (the specific red flags and the evidence for each), and what
was done in response. Be precise and factual, cite specific numbers rather
than vague characterizations, and do not speculate beyond what the evidence
supports. Write only the narrative text."""
    result = llm.invoke(prompt)
    return {"draft_narrative": result.content, "critic_feedback": ""}


def critic_node(state: SARState) -> dict:
    llm = get_llm()
    red_flags_ref = "\n".join(
        f"- {rf['key']}: {rf['description']}" for rf in RED_FLAGS
    )
    prompt = f"""You are a senior compliance reviewer checking a draft SAR
narrative before it is filed. Here is the case evidence:

{state['retrieved_evidence']}

Here is the draft narrative to review:

{state['draft_narrative']}

Here are red flag categories a complete narrative for this kind of case
should address if the evidence supports them:
{red_flags_ref}

Check the draft against these requirements: does it cite specific account
numbers, dates, and dollar amounts rather than vague language; does it
address each red flag category the evidence actually supports; does it
avoid speculating beyond what the evidence shows; is the who, what, when,
how much, and why all present and specific.

If the draft meets all of these, respond with a first line that says
exactly: APPROVED
If it does not, respond with a first line that says exactly: REVISE
followed by specific, actionable feedback on exactly what is missing or
wrong, citing which red flag categories are missing or which claims lack
citations."""
    result = llm.invoke(prompt)
    content = result.content.strip()
    verdict = "APPROVED" if content.upper().startswith("APPROVED") else "REVISE"
    feedback = content if verdict == "REVISE" else ""
    return {
        "critic_verdict": verdict,
        "critic_feedback": feedback,
        "revision_round": state.get("revision_round", 0) + 1,
    }


def route_after_critic(state: SARState) -> str:
    if state["critic_verdict"] == "APPROVED" or state["revision_round"] >= MAX_CRITIC_ROUNDS:
        return "finalize"
    return "revise"


def finalize_node(state: SARState) -> dict:
    return {"final_narrative": state["draft_narrative"]}


def build_graph():
    graph = StateGraph(SARState)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("drafting", drafting_node)
    graph.add_node("critic", critic_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("retrieval")
    graph.add_edge("retrieval", "analysis")
    graph.add_edge("analysis", "drafting")
    graph.add_edge("drafting", "critic")
    graph.add_conditional_edges("critic", route_after_critic, {"revise": "drafting", "finalize": "finalize"})
    graph.add_edge("finalize", END)

    return graph.compile()


def run_multiagent(case_text: str) -> dict:
    app = build_graph()
    initial_state: SARState = {
        "case_text": case_text,
        "retrieved_evidence": "",
        "red_flags_identified": "",
        "draft_narrative": "",
        "critic_feedback": "",
        "critic_verdict": "",
        "revision_round": 0,
        "final_narrative": "",
    }
    final_state = app.invoke(initial_state, {"recursion_limit": 25})
    return final_state
