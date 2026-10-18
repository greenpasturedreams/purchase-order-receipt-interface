# System requirements, user stories and traceability

**Baseline:** v1 proposed. “Reference tested” means the Python/SQLite behavior passed automated tests; SQL Server, live integration and business UAT are separate gates. There are no signed requirements approvals in this case study.

## User stories

- **US01, receiving clerk:** As a receiving clerk, I want a valid partial receipt to update the correct PO line and stock once, so available quantities remain accurate.
- **US02, external-system owner:** As a sender, I want to retry after an uncertain response without creating another receipt, so recovery is safe.
- **US03, inventory controller:** As an inventory controller, I want a full correction tied to its original receipt, so changes remain traceable.
- **US04, buyer:** As a buyer, I want actionable errors for invalid PO, units and quantities, so I can correct the source issue.
- **US05, support analyst:** As a support analyst, I want to trace each attempt to a business key and outcome, so I can investigate without changing database records directly.

## Functional requirements and acceptance criteria

| ID | System requirement | Acceptance criteria | Business / story |
|---|---|---|---|
| FR01 | Validate strict version-1 JSON contract before posting | Reject missing, extra or duplicate keys; wrong types/IDs; invalid UTC syntax; >16 KiB body. No business writes. | BR03, US04 |
| FR02 | Locate and validate PO line/master data | Unknown PO/line, mismatched UOM, pre-creation time or closed line for a new receipt returns the defined error. | BR02, US01/04 |
| FR03 | Support positive partial receipts within ordered quantity | Exact three-decimal arithmetic; reject zero/negative/excess precision; sum net received ≤ ordered. Distinct partial IDs can complete the order. | BR02, US01 |
| FR04 | Make successful submissions idempotent | Same source/key and normalized content returns original reference without extra business movement. Changed content returns 409. Rejected keys may be corrected and resubmitted. | BR01, US02 |
| FR05 | Support one full reversal per original receipt | New reversal key must reference matching dimensions/quantity and valid sequence; no double or partial reversal; closed-line correction allowed; no negative balances. | BR02, US03 |
| FR06 | Post ledger, PO and inventory atomically | Injected failure after ledger insert leaves all three business stores unchanged; identical retry can subsequently post. Concurrent requests cannot over-receive. | BR01/02, US01/02 |
| FR07 | Retain an attempt audit | Successful, duplicate, rejected and recoverable technical outcomes are recorded; duplicate attempt creates audit only. Production audit-store outage recovery is separately gated. | BR03, US05 |
| FR08 | Enable source-to-target tracing and reconciliation | A known source/receipt key locates attempts, ledger, PO and inventory. Seeded receipt/reversal totals reconcile to zero opening balances. | BR02/03, US05 |
| FR09 | Enforce documented clock rules | Real UTC date/time, no more than five minutes ahead, no event before PO creation, and reversal not before original. Exact five-minute boundary accepted. | BR02, US03/04 |
| FR10 | Enforce the version-1 source and warehouse scope | WMS_DEMO/MAIN supported; other registered-looking values explicitly rejected rather than defaulted. | BR02/03, US01 |
| FR11 | Return stable response semantics and ownership guidance | Posted/duplicate/conflict/business/technical outcomes have documented statuses and codes. Technical failure indicates rollback and identical retry. | BR03, US02/04/05 |

## Nonfunctional and operational requirements: proposals requiring validation

| ID | Proposed requirement | Acceptance method | Status |
|---|---|---|---|
| NFR01 | Meet an agreed throughput/latency target without violating balances | Agree volume, concurrency and P95 latency; target-engine load test and reconciliation | Target not set; not measured |
| NFR02 | Authenticate sender and bind source authorization to identity; least privilege and encrypted transport | Invalid identity/source tests, permission review, TLS verification | Design only; no live endpoint |
| NFR03 | Apply approved audit retention, redaction, access and recovery policy | Security/business policy approval; backup/restore and audit-store outage drills | Policy pending |
| NFR04 | Make production exceptions observable and recoverable | Alerting tests, failed-attempt queue/reconciliation, retry/deadlock and recovery drills | Operational integration pending |

## Requirements traceability matrix

| Requirement | Design / implementation evidence | Automated reference tests | Current status |
|---|---|---|---|
| FR01 | Interface specification; src/interface.py normalize | TC11, TC12, TC13, TC14, TC27, TC28 | Reference tested |
| FR02 | Process sequence; PO validation; SQL Server core | TC04, TC05, TC06, TC07, TC14 | Reference tested; SQL Server pending |
| FR03 | Quantity mapping and PO balance checks | TC01, TC08, TC09, TC10, TC26 | Reference tested |
| FR04 | Canonical hash; successful ledger key; conflict handling | TC02, TC03, TC24, TC25 | Reference tested |
| FR05 | Reversal reference and unique-reversal rule | TC16, TC17, TC18, TC19, TC20, TC21, TC27 | Reference tested |
| FR06 | Protected transaction; fault injection; unique keys | TC01, TC22, TC23 | Reference tested; target-engine concurrency pending |
| FR07 | Attempt audit and rejection/rollback paths | TC02, TC22, TC28 | Reference tested; production audit recovery pending |
| FR08 | run_demo.py reconciliation; sqlserver/03_trace_and_reconcile.sql | TC01, TC16, TC22; demo reconciliation report | Reference evidence; SQL Server queries not executed |
| FR09 | Timestamp normalization and comparisons | TC14, TC18 | Reference tested |
| FR10 | Source/warehouse validation; CR001 baseline boundary | TC15 | Reference tested |
| FR11 | Response/error table and training guide | TC01–TC28 check applicable outcomes/codes; response display in CLI demo | Reference tested; human usability/UAT pending |
| NFR01 | SDLC load-test gate | None | Pending target and environment |
| NFR02 | Architecture and interface production gates | None | Design only |
| NFR03 | Retention/access/recovery requirements | None | Proposed |
| NFR04 | Support and deployment plan | TC22 covers one local injected rollback only | Production recovery pending |

Actual results are in [test_results.txt](../reports/test_results.txt) and [validation.json](../reports/validation.json). Business UAT in [05_TEST_PLAN_AND_UAT.md](05_TEST_PLAN_AND_UAT.md) remains unexecuted. Reference tests are not customer sign-off or evidence of SQL Server execution.
