# SQL Server implementation and execution gate

**Status: authored, NOT EXECUTED against SQL Server in this case study.** The 28 passing automated tests use the Python/SQLite reference. They do not certify these scripts, locking behavior or cross-engine hash parity.

## Prerequisites

Use an isolated **new, empty demonstration database** and a currently supported SQL Server engine with SSMS or sqlcmd. The scripts use CREATE OR ALTER PROCEDURE (SQL Server 2016 SP1+) and TRY_CONVERT/THROW. They are **not compatible with SQL Server 2000/2005/2008** as written. A legacy employer environment requires a separate compatibility/design assessment.

No database is created, dropped or reset by the scripts. The schema script creates objects and inserts fictional seed data, so run it once in the empty demo database. It is not a migration for an existing ERP database.

## Execution order

1. Select the new demo database in SSMS.
2. Run [01_schema.sql](01_schema.sql).
3. Run [02_process_receipt.sql](02_process_receipt.sql).
4. Run [04_smoke_tests.sql](04_smoke_tests.sql) once; inspect each response and assertion.
5. Run [03_trace_and_reconcile.sql](03_trace_and_reconcile.sql). Reconciliation difference queries should return zero rows for this seeded scenario.
6. Record engine/version, execution date, scripts/build, expected vs actual results, defects and retests. Only then update the SQL Server execution status.

The smoke sequence posts 25 units, retries, conflicts at 30, injects rollback on a new key, then reverses the original. Expected ledger: one +25 receipt and one −25 reversal; net PO/stock zero. Initial successful payload hash must match the reference's documented canonical hash. Smoke tests deliberately change this demo database; use another new database for a clean rerun.

## Boundary and pending tests

ProcessReceipt is an **internal normalized-parameter core**, not a public JSON adapter. The caller must first perform the strict schema, identifier-length/character, type and UTC validation in the interface specification. Truncated typed arguments are not a substitute for rejecting an invalid JSON request. The procedure does additional business/quantity validation and owns its transaction; call it without an existing transaction.

The adapter must authenticate and authorize the sender, map approved response messages, restrict procedure execution, handle audit/transport outages and remove/restrict the demonstration fault-injection capability before production. No such adapter is deployed here.

Beyond smoke tests, execute every applicable reference business scenario through the target adapter; test simultaneous same-key requests, different-key over-receipts, reversal races, deadlocks, lost responses before/after commit, restart recovery and realistic load. Verify audit and business reconciliation after each test. Review lock scope and isolation with the database team.

## Microsoft references

- [CREATE PROCEDURE](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-procedure-transact-sql): syntax and CREATE OR ALTER availability.
- [Table hints](https://learn.microsoft.com/en-us/sql/t-sql/queries/hints-transact-sql-table): UPDLOCK/HOLDLOCK behavior and lock scope.
- [TRY/CATCH](https://learn.microsoft.com/en-us/sql/t-sql/language-elements/try-catch-transact-sql) and [SET XACT_ABORT](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-xact-abort-transact-sql): transaction error handling.

These references inform the proposed design. Documentation review does not replace executing the code on the target engine.
