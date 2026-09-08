"""Formats the raw case JSON into a plain text evidence block every agent reads from."""

from __future__ import annotations

import json
from pathlib import Path


def load_case(path: str | Path) -> dict:
    with open(path) as f:
        return json.load(f)


def format_case_as_text(case: dict) -> str:
    lines = [
        f"Case: ring_id {case['ring_id']}, typology {case['typology']}",
        f"Source: {case['source']}",
        f"Transactions: {case['n_transactions']}, Accounts involved: {case['n_accounts']}",
        f"Total amount moved (approx USD equivalent, see note below): {case['total_amount_usd_approx']:,.2f}",
        f"Note on amounts: {case['fx_note']}",
        f"Date range: {case['date_range'][0]} to {case['date_range'][1]}",
        "",
        "Transaction detail (chronological). Each transaction's native currency amount "
        "is shown along with its approximate USD equivalent so magnitudes across "
        "different currencies can be compared directly:",
    ]
    for t in case["transactions"]:
        lines.append(
            f"  {t['ts']}  from account {t['from_account']} (bank {t['from_bank']})  "
            f"to account {t['to_account']} (bank {t['to_bank']})  "
            f"amount {t['amount_paid']:,.2f} {t['currency_paid']} "
            f"(approx {t['amount_usd_approx']:,.2f} USD)"
        )
    lines.append("")
    lines.append("Known account/entity records for accounts in this ring:")
    for a in case["accounts"]:
        lines.append(
            f"  account {a['account']}  bank {a['bank_name']} (id {a['bank_id']})  "
            f"entity_id {a['entity_id']}  entity_name {a.get('entity_name') or 'not recorded'}"
        )
    return "\n".join(lines)
