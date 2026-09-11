# Does a 4 agent pipeline draft a better SAR than one agent alone

[![tests](https://github.com/JAYANSHUBADLANI/sar-multiagent-drafting/actions/workflows/tests.yml/badge.svg)](https://github.com/JAYANSHUBADLANI/sar-multiagent-drafting/actions/workflows/tests.yml)

A multi-agent LangGraph pipeline, retrieval, analysis, drafting, critic,
compared against a single model doing the same job in one pass, drafting
the narrative section of a Suspicious Activity Report for a real flagged
money laundering case, entirely on a local model, no API keys, no cloud.

## Headline result

On the one real case tested, the 4 agent pipeline did not produce a more
complete narrative than the single agent baseline by the coverage metric
defined in advance: both adequately cited all 6 of the 6 real red flags
this case's data supports. The multi-agent pipeline took 491.5 seconds
against the baseline's 141.7 seconds, about 3.5 times slower, for an
equal, maximum score. Neither approach hallucinated an account number
that was not actually one of the 14 real accounts in this case, in either
run.

An earlier version of this project's own ground truth compared dollar
figures across 8 different currencies without converting them first, and
both approaches missed the same red flag under that flawed yardstick.
That gap traced back to my own uncorrected arithmetic, not to either
agent's reasoning: fixed in `data_prep.py` and described in full in
`PROGRESS.md`, since it changed the actual measured result and is worth
being direct about rather than quietly editing away.

## The case

Ring 246, typology FAN-OUT, from the IBM AML synthetic dataset already
loaded in this portfolio's `laundering-ring-detection` project. One
account, 8045F4500 at bank 11128, sent 13 transfers to 13 distinct
accounts across 12 distinct banks and 8 currencies (Swiss Franc, Canadian
Dollar, US Dollar, Yuan, Euro, Yen, Saudi Riyal, Rupee) between September
7 and September 11, 2022, ranging from 270.35 US Dollars to 295,519.18 US
Dollars once every native currency amount is converted to an approximate
US Dollar equivalent (`amount_usd_approx` in the saved case file, ballpark
September 2022 rates, see `src/data_prep.py`). The transfers' native
currency amounts are not directly comparable to each other without that
conversion, a 6,242,980.34 unit Yen transfer is only about 43,657 US
Dollars, a mistake this project's own first pass made, see `PROGRESS.md`.
A real labeled ring, not a synthetic or hand written example, pulled
directly from that project's DuckDB. See `src/data_prep.py`.

## Ground truth, decided before running either approach

`src/red_flags_reference.py` states six red flags this case's actual
numbers support, worked out by reading the raw transaction data directly,
each with the specific account numbers, dates, or dollar amounts a
narrative needs to cite to count as adequately covering that flag:

1. Single source fan out to 13 accounts across 12 banks in 5 days
2. Multi currency, multi jurisdiction spread across 8 currencies
3. Irregular, inconsistent transaction amounts
4. High velocity, all 13 transfers within a 5 day window
5. One dominant outlier transfer, and a second, smaller but still
   notable one, once amounts are compared in a common currency
6. No apparent legitimate business purpose evident in the data

## The two approaches

**Single agent baseline.** One model call, the full case data, one
instruction naming everything a SAR narrative needs. `src/baseline_single_agent.py`.

**4 agent pipeline.** Retrieval organizes the raw facts without analysis.
Analysis identifies red flags with citations from the organized facts.
Drafting writes the narrative from the identified flags. Critic checks the
draft against the same red flag categories and either approves or sends it
back with specific feedback, up to 2 rounds. `src/agents.py`. Both
approaches use the same model, qwen2.5:14b via Ollama, and the same case
text.

Intermediate agent messages are kept as plain text rather than forced JSON:
a 14B local model is meaningfully less reliable at strict structured
output than a frontier API model, and the question being tested is
whether specialization and critique improve the final narrative, not
whether inter agent messages parse as JSON. The one place structure is
enforced is the critic's verdict, a literal APPROVED or REVISE first line
checked directly.

## Results

| | Baseline | Multi-agent |
|---|---|---|
| Red flags adequately cited | 6 / 6 | 6 / 6 |
| Runtime | 141.7s | 491.5s |
| Critic revision rounds | n/a | 1 |
| Hallucinated account numbers | 0 | 0 |

Both approaches correctly identify 295,519.18 US Dollars on September 9 as
the dominant outlier and the 6,242,980.34 Yen transfer (about 43,657 US
Dollars) as a secondary one, once the case data hands both agents the US
Dollar equivalent directly rather than requiring either one to convert 8
currencies itself. An earlier run, before that conversion was added, is
the one that produced the 5 of 6 numbers in `PROGRESS.md`; the earlier
gap traced back to my own ground truth comparing unconverted currency
figures, not to a reasoning difference between the two approaches. Full
reasoning trail, including how that was caught, in `PROGRESS.md`.

## Sharpest ways this could be wrong

One case. This is a demonstration on a real example, not a claim that
generalizes: a single ring at a perfect coverage score for both approaches
says nothing about whether the pipeline versus single agent gap holds on
harder cases, other typologies, or a case where the correct US Dollar
equivalent is not simply handed to both agents in the input data.

The critic reviewing the same model's own analysis output is a real design
limitation, not incidental: an independent second model instance, or a
model with access to the raw evidence rather than only the drafted
narrative, might behave differently. That was not tried, and with both
approaches now at the maximum score there was no remaining gap on this
case for it to have closed anyway.

Coverage citation is a specific, checkable metric chosen because it can be
scored without another LLM call and without my own subjective read of
narrative quality, but it does not capture everything a compliance
reviewer would judge a SAR narrative on. The observation that the
multi-agent analysis stage produces a more itemized, per flag structure
than the baseline's continuous prose is recorded in `PROGRESS.md` as
something noticed, not something scored, because no objective way to
measure that without it becoming a stated preference was found.

The 3.5x runtime gap is specific to this hardware and this model size; it
is not a general claim about multi-agent orchestration cost versus a
single call, only about what actually happened running qwen2.5:14b on
this machine for this case. It is also not the same multiplier as the
first, uncorrected run's 6x: giving both agents the pre-computed currency
conversion shortened the baseline's generation somewhat more than the
pipeline's, likely because the baseline had less analysis to redo without
it, which is itself a small illustration of how sensitive a runtime ratio
like this is to what exactly the input data already contains.

## Reproducing this

Needs Ollama running locally with `qwen2.5:14b` pulled, and the
`laundering-ring-detection` project's DuckDB present at its existing path
in this portfolio, since `data_prep.py` reads directly from it rather than
copying the source data into this project.

```
cd sar-multiagent-drafting
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd src
python3 data_prep.py
python3 run_experiment.py
cd ..
python3 -m pytest tests/ -v
```

The full 4 agent run takes on the order of 10 minutes on the hardware this
was built on (Apple M5, 16GB RAM); `run_experiment.py` runs the baseline
first so a result is available quickly even if the multi-agent run is
still going.

## Test suite

9 of 9 tests pass, covering the evaluation scoring logic (coverage
citation detection, hallucinated account number detection), the case data
integrity, the case-to-text formatter, and the saved comparison results.
These tests do not call the local model; they check the deterministic
scoring and data logic, since re-running live model calls on every test
run would make the suite slow and the local model's output is not
deterministic across runs in the first place.
