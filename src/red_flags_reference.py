"""
A ground truth reference of the red flags this specific case actually
supports, worked out by reading the raw transaction data directly (see
data_prep.py's output), not by asking an LLM first and checking its
homework after the fact. This is what both the multi-agent pipeline and
the single-agent baseline are scored against in evaluate.py: does the
generated narrative name each red flag and cite the specific evidence
(account, date, amount) that supports it.

These map to categories in FinCEN's general red flag guidance for money
laundering (Advisory FIN-2014-A005 and related SAR guidance), not
quotations, restated in terms of what this specific case's numbers show.
"""

RED_FLAGS = [
    {
        "key": "single_source_fan_out",
        "description": (
            "A single account, 8045F4500 at bank 11128, sent funds to 13 "
            "distinct accounts at 12 distinct banks within a 5 day window, "
            "a dispersal pattern rather than a small number of ordinary "
            "counterparties."
        ),
        "requires_citation_of": ["8045F4500", "11128", "13", "12"],
    },
    {
        "key": "multi_currency_multi_jurisdiction",
        "description": (
            "The 13 outbound transfers span at least 8 distinct currencies "
            "(Swiss Franc, Canadian Dollar, US Dollar, Yuan, Euro, Yen, "
            "Saudi Riyal, Rupee), consistent with deliberate jurisdictional "
            "spread rather than a single ordinary business relationship."
        ),
        "requires_citation_of": ["currency", "Yen", "Euro"],
    },
    {
        "key": "irregular_amounts",
        "description": (
            "Transaction amounts range from 270.35 US Dollars to 295,519.18 "
            "US Dollars, roughly a thousandfold spread with no consistent "
            "size or pattern that would match recurring invoices, payroll, "
            "or a stated business purpose."
        ),
        "requires_citation_of": ["270", "295,519", "295519"],
    },
    {
        "key": "high_velocity_short_window",
        "description": (
            "All 13 transfers occurred within 5 days, September 7 to "
            "September 11, 2022, several on the same calendar day, "
            "a velocity inconsistent with routine periodic payments."
        ),
        "requires_citation_of": ["September", "2022", "5 day"],
    },
    {
        "key": "outlier_large_transfers_embedded",
        "description": (
            "In real dollar terms (native currency amounts are not directly "
            "comparable across this ring's 8 currencies without conversion, "
            "see PROGRESS.md), one transfer dominates: 295,519.18 US Dollars "
            "on September 9, roughly 6 to 7 times larger than every other "
            "transfer once converted to a common currency, including the "
            "6,242,980.34 Yen transfer on September 11, which looks large "
            "in its native units but converts to only approximately "
            "43,657 US Dollars, itself still notably larger than the "
            "roughly 270 to 22,000 US Dollar range of the remaining 11 "
            "transfers. A narrative that treats the Yen figure's raw "
            "magnitude as comparable to the US Dollar figure without "
            "converting currencies first is citing the numbers but drawing "
            "the wrong comparison from them."
        ),
        "requires_citation_of": ["295,519", "295519"],
    },
    {
        "key": "no_apparent_business_purpose",
        "description": (
            "Nothing in the available account or transaction data indicates "
            "a legitimate business relationship between account 8045F4500 "
            "and the 13 unrelated receiving accounts across 12 banks and "
            "multiple currencies."
        ),
        "requires_citation_of": ["business", "purpose", "relationship"],
    },
]
