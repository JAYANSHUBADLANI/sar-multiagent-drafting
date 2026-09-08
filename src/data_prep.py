"""
Pulls one real flagged ring (ring_id 246, typology FAN-OUT, from the IBM AML
dataset already loaded in the laundering-ring-detection project) out of its
DuckDB and saves it as the case file this project's agents work from: the
transaction evidence a compliance analyst would actually have in hand when
starting a SAR, not a synthetic or hand written example.

FAN-OUT: one account receiving large inbound amounts and then rapidly
distributing them out to many other accounts, a classic layering pattern.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

RING_ID = 246
TYPOLOGY = "FAN-OUT"
SOURCE_DB = str(
    Path(__file__).resolve().parents[2]
    / "laundering-ring-detection" / "data" / "interim" / "aml.duckdb"
)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# Approximate September 2022 spot rates, units of local currency per 1 USD,
# used only to rank transactions by rough real world magnitude. These are
# ballpark monthly figures, not the exact rate on each transaction's exact
# date, and that imprecision is stated in README.md rather than presented
# as precise. Caught late: the raw transaction amounts across currencies
# are not directly comparable, a 6,242,980 unit Yen transfer is nowhere
# near a 6,242,980 unit US Dollar transfer in real terms, see PROGRESS.md.
USD_PER_UNIT = {
    "US Dollar": 1.0,
    "Swiss Franc": 1 / 0.97,
    "Canadian Dollar": 1 / 1.30,
    "Yuan": 1 / 6.95,
    "Euro": 1 / 0.99,
    "Yen": 1 / 143.0,
    "Saudi Riyal": 1 / 3.75,
    "Rupee": 1 / 79.5,
}


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    con = duckdb.connect(SOURCE_DB, read_only=True)

    txns = con.execute(
        """
        SELECT from_bank, from_account, to_bank, to_account, ts,
               amount_paid, currency_paid, amount_received, currency_received,
               payment_format
        FROM patterns_hi_small
        WHERE ring_id = ? AND typology = ?
        ORDER BY ts
        """,
        [RING_ID, TYPOLOGY],
    ).fetchdf()

    txns["amount_usd_approx"] = txns.apply(
        lambda r: round(r["amount_paid"] * USD_PER_UNIT[r["currency_paid"]], 2), axis=1
    )

    accounts_involved = sorted(set(txns["from_account"]) | set(txns["to_account"]))
    account_info = con.execute(
        f"""
        SELECT DISTINCT bank_name, bank_id, account, entity_id, entity_name
        FROM accounts_hi_small
        WHERE account IN ({','.join(['?'] * len(accounts_involved))})
        """,
        accounts_involved,
    ).fetchdf()

    case = {
        "ring_id": RING_ID,
        "typology": TYPOLOGY,
        "source": "IBM AML synthetic dataset (ealtman2019), HI-Small split, real labeled ring, "
                  "reused from the laundering-ring-detection project in this portfolio",
        "n_transactions": len(txns),
        "n_accounts": len(accounts_involved),
        "total_amount_usd_approx": float(txns["amount_usd_approx"].sum()),
        "fx_note": "amount_usd_approx uses ballpark September 2022 monthly average rates, "
                   "see USD_PER_UNIT in data_prep.py, not the exact rate on each transaction's date",
        "date_range": [str(txns["ts"].min()), str(txns["ts"].max())],
        "transactions": json.loads(txns.to_json(orient="records", date_format="iso")),
        "accounts": json.loads(account_info.to_json(orient="records")),
    }

    with open(DATA_DIR / "case_246.json", "w") as f:
        json.dump(case, f, indent=2)

    print(f"ring {RING_ID} ({TYPOLOGY}): {len(txns)} transactions, {len(accounts_involved)} accounts")
    print(f"total amount (approx USD): ${case['total_amount_usd_approx']:,.2f}")
    print(f"date range: {case['date_range'][0]} to {case['date_range'][1]}")
    top3 = txns.nlargest(3, "amount_usd_approx")[["ts", "amount_paid", "currency_paid", "amount_usd_approx"]]
    print("largest transfers by approx USD value:")
    print(top3.to_string(index=False))
    print(f"saved to {DATA_DIR / 'case_246.json'}")


if __name__ == "__main__":
    main()
