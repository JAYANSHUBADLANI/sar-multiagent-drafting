# Progress log

The question: does a 4-agent pipeline (retrieval, analysis, drafting,
critic) actually produce a better Suspicious Activity Report narrative
than one model doing the whole job in a single pass, on a real flagged
case, running entirely on a local model, qwen2.5:14b through Ollama.

Picked a real case rather than a synthetic one: ring_id 246, typology
FAN-OUT, from the IBM AML dataset already loaded in the
laundering-ring-detection project's DuckDB. One account, 8045F4500,
sending to 13 distinct accounts across 12 banks and 8 currencies over 5
days, amounts ranging from 270.35 to the equivalent of 6,242,980.34. Real
labeled ring, not invented.

Worked out the ground truth red flags by reading the raw transaction data
myself before building or running any agent, in red_flags_reference.py:
six categories this specific case's numbers actually support, each with
the exact account numbers, dates, or dollar amounts a narrative would need
to cite to count as adequately covering that flag rather than gesturing at
it vaguely. This is the yardstick both approaches get measured against,
decided before seeing either one's output.

Kept the LangGraph pipeline to plain text between nodes rather than
forcing structured JSON output at every step. A 14B local model is
noticeably less reliable at strict JSON than a frontier API model, and
what is actually being tested here is whether specialization and a
critique step improve the final narrative, which does not require the
intermediate messages between agents to be machine parseable. The one
place I did enforce a specific format is the critic's verdict, a literal
APPROVED or REVISE first line, checked directly rather than trusted as
JSON.

First real run: single agent baseline finished in 94.2 seconds. The 4
agent pipeline, including one critic revision round, finished in 581.9
seconds, nearly 10 minutes, about 6 times slower.

Scored both against the 6 red flags. Both adequately cited 5 of 6, and it
was the same one missing in both: outlier large transactions embedded
among smaller ones. I checked this was a genuine gap and not a scoring
formatting mismatch by grepping both narratives for the actual dollar
figures directly, and traced it into the multi-agent pipeline's own
intermediate analysis output to see it was not something drafting or the
critic introduced independently.

Caught a real mistake in my own ground truth while doing that tracing,
not in the agents: I had written the outlier red flag as two transfers,
295,519.18 US Dollars and the equivalent of 6,242,980.34 Yen, being
comparably large. I built that comparison by looking at the raw numeric
values in data_prep.py's saved case file without converting currencies
first, and a transaction paid in Yen units is not the same magnitude as
the same numeral in US Dollars. Converted both to approximate US Dollars
using ballpark September 2022 rates: the Yen transfer is actually about
43,657 US Dollars, a real but much smaller figure than 295,519, not a
comparable twin outlier. My original ground truth was asking both agents
to treat two currency incomparable numbers as equivalent scale, which was
my error, not evidence that either agent's reasoning was worse than mine,
and I want that stated plainly rather than buried: the first "both missed
the same flag" result was measuring my own uncorrected arithmetic, not a
real gap in either narrative.

Fixed data_prep.py to compute an approximate US Dollar equivalent per
transaction (USD_PER_UNIT, stated as ballpark monthly rates, not exact
daily rates, in a comment there) and fed that alongside the native
currency amount to every agent through case_formatter.py, rather than
leaving currency conversion as an implicit expectation. Corrected
red_flags_reference.py to describe the real picture: one dominant
outlier, not two comparable ones. Re-ran data_prep.py and the full
experiment.

Second real run: single agent baseline finished in 141.7 seconds, the 4
agent pipeline in 491.5 seconds, still one critic round, about 3.5 times
slower this time. Both approaches now adequately cite all 6 of 6 red
flags. Once the case data handed both agents the correct US Dollar
equivalent directly, instead of requiring them to convert 8 different
currencies themselves, both got the outlier comparison right immediately.
That itself is worth keeping as a finding: the earlier gap traced back to
an arithmetic and data representation problem, not a reasoning depth
problem the extra agents or critic step would have been positioned to
fix anyway, since none of the four roles in the pipeline were ever asked
to do currency conversion as a distinct step.

Headline finding, stated plainly rather than softened, now on the
corrected run: on this one real case, the 4 agent pipeline did not
produce a more complete narrative than the single agent baseline by the
coverage metric defined in advance, both hit the maximum of 6 of 6, and
cost about 3.5 times the wall clock time and roughly 6 times the model
calls to get there. Zero hallucinated account numbers in either
narrative in both runs, which is a real result worth keeping, not just an
absence of a problem: a small local model asked to write about 14
specific real account numbers across 13 transactions did not invent a
15th one in either condition, before or after the currency fix.

What the multi-agent version arguably did do better, not captured by the
binary coverage metric: the analysis stage output is more explicit and
itemized per red flag category with its own evidence subsection than the
baseline's more continuous narrative prose, which could matter for a human
reviewer's ability to audit the reasoning even where the two land on the
same coverage number. I did not build a metric for this because I could
not think of an objective way to score narrative organization without it
turning into my own subjective preference, so it is recorded here as an
observation rather than a result.

Left undone: only one case was tested. A single example, even a real one,
is a demonstration, not a claim that generalizes, and I am stating that
plainly rather than implying six-flag coverage on one ring says anything
about the average case. Currency conversion was fixed by pre-computing it
in data_prep.py and handing the result to every agent, not by adding a
fifth agent whose job is specifically to normalize units before analysis
begins; whether a dedicated currency-normalization step inside the
pipeline itself, rather than in the data preparation script, would change
anything was not tested, since precomputing it made the rest of the
comparison cleaner to reason about. Did not test whether a larger local
model, or more critic rounds, changes anything further; MAX_CRITIC_ROUNDS
is capped at 2 in agents.py and both real runs only needed one revision
round to reach APPROVED, so the cap itself was never stress tested. Did
not compare against qwen2.5:7b to see whether the smaller, faster model
already installed produces a meaningfully different coverage number for a
fraction of the runtime, which is the more interesting speed versus
quality question this project's own numbers raise but do not answer.
