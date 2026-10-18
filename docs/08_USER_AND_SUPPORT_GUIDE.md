# User and support guide

## Run the demonstration

Python 3.12+ is sufficient; no external packages or database server are required for the reference demo. From the project root:

```bash
python run_demo.py
```

This runs isolated tests and a fresh example flow, then saves evidence under `reports/`. It does not change your separate CLI database. The demo clock is fixed at October 18, 2026, 12:00 UTC so the supplied examples remain repeatable.

To try individual payloads:

```bash
python src/cli.py examples/valid_receipt.json
python src/cli.py examples/valid_receipt.json
python src/cli.py examples/full_reversal.json
```

On a fresh default CLI database, the expected outcomes are POSTED, DUPLICATE and POSTED. The database persists in ignored `runtime/demo.db`. Repeating these commands later may return duplicates. To start another independent exercise without deleting anything, use a new path:

```bash
python src/cli.py examples/valid_receipt.json --db runtime/practice2.db
```

The CLI exits 0 for posted/duplicate and 1 for a rejection or technical error. It displays HTTP-like status fields but sends no HTTP request.

## Understand the result

| Outcome | Meaning | Action |
|---|---|---|
| POSTED | One ledger movement and balance update committed | Retain processing reference |
| DUPLICATE | The same successful request was already processed | Keep original reference; do not invent a new ID just to retry |
| REJECTED / conflict | A posted ID was reused with different data | Investigate original submission; use an approved reversal/new receipt workflow for correction |
| REJECTED / business validation | No business posting occurred | Buyer/receiving correct the source issue; a previously rejected key may be resubmitted |
| TECHNICAL_ERROR | Local processing rolled back | Support resolves issue; sender retries identical request |

## Partial receipts and corrections

To receive the rest of a 100-unit line after 25 units, submit a **new receipt ID** with quantity 75.000. The first ID remains associated with its original 25.000-unit business receipt. Changing that original ID to 75.000 is a conflict.

For an incorrect successful receipt, v1 supports one full reversal referencing the original ID, then a new corrected receipt with a new ID. The reversal must use matching dimensions and quantity, cannot predate the original or create negative stock, and is still allowed if the PO line subsequently closes. No manual ledger edits or partial reversals are demonstrated.

## Support triage and tracing

1. Capture source/receipt key, attempt time, error code, original request and processing reference where present.
2. Check attempt history before retrying or changing any ID.
3. For business errors, involve the owner of PO status, UOM or stock availability; do not bypass the rule in SQL.
4. For conflicts, compare the normalized business fields with the original posting.
5. For technical failures, check transaction/audit evidence and determine whether an acknowledgement was lost after commit. Identical retry is safe under the implemented key rule.
6. Reconcile ledger deltas to PO received quantities and stock with the appropriate opening balances and movement scope.

SQL Server tracing queries are in [03_trace_and_reconcile.sql](../sqlserver/03_trace_and_reconcile.sql). They are supplied for target-engine execution and have not been run here. The demo evidence JSON contains the same conceptual sequence in SQLite.

## Knowledge check

- A retry returns DUPLICATE. Should stock increase again? **No.**
- A successful ID is resent with a new quantity. What happens? **Conflict; existing data stays unchanged.**
- A quantity was rejected before posting. Can its ID be used after correction? **Yes.**
- Can another ID reverse the same original a second time? **No.**
- Does a passing local test suite mean business UAT is signed or SQL Server is validated? **No; these are separate acceptance gates.**
