# Test plan and user acceptance testing pack

## Strategy and environments

| Layer | Scope | Evidence status |
|---|---|---|
| Reference functional tests | JSON validation, business rules, duplicate/reversal behavior and SQLite transactions | 28 automated tests executed; see reports |
| Reference concurrency | Two competing 60-unit receipts against a 100-unit PO line | Executed on local SQLite; one posts, one rejects |
| SQL Server smoke tests | Core receipt/retry/conflict/fault/reversal, canonical hash and balances | Script supplied; NOT EXECUTED |
| SQL Server integration | Adapter, engine constraints, locks, deadlocks, retries and audit recovery | Pending environment and implementation |
| Security and performance | Identity binding, access, TLS, realistic load and recovery | Not implemented/measured |
| Business UAT | Receiving/buyer/support validate business fit and usability | Prepared below; not executed or signed |

**Entry criteria:** proposed baseline and test data available; environment isolated; expected results documented. **Exit criteria for a real release:** no unresolved critical defects, reconciliation passes, SQL Server/integration/security/load gates pass, business UAT completed, owners trained and go/no-go documented. The reference suite alone does not satisfy release exit criteria.

## Automated test inventory

| Test ID | Scenario and expected behavior |
|---|---|
| TC01 | Valid 25-unit partial receipt posts ledger, PO and stock once |
| TC02 | Identical retry returns same reference, one business posting, two attempt records |
| TC03 | Same successful key with changed quantity returns conflict and preserves balance |
| TC04 | Unknown PO rejected |
| TC05 | Unknown PO line rejected |
| TC06 | New receipt against closed line rejected |
| TC07 | UOM mismatch rejected |
| TC08 | Zero, negative, scientific, excessive scale/size or non-string quantity rejected |
| TC09 | Over-receipt rejected with no ledger posting |
| TC10 | Distinct 25 + 75 partial receipts complete 100 units; next fraction rejected |
| TC11 | Invalid JSON rejected |
| TC12 | Missing, unknown and duplicate JSON keys rejected |
| TC13 | Unsupported version, wrong integer types and invalid identifiers rejected |
| TC14 | Invalid/non-UTC/future/pre-PO time rejected; exact +5 minutes accepted |
| TC15 | Unknown source and non-MAIN warehouse rejected |
| TC16 | Full reversal restores balances; its identical retry does not reverse twice |
| TC17 | Missing original or mismatched PO/UOM dimensions rejected |
| TC18 | Partial reversal or reversal before original time rejected |
| TC19 | Different second reversal ID cannot reverse an original twice |
| TC20 | Original receipt can be reversed after PO line closure |
| TC21 | Reversal cannot create negative available balance |
| TC22 | Injected post-ledger failure rolls back ledger, PO and stock; identical retry works |
| TC23 | Concurrent competing receipts cannot exceed ordered quantity |
| TC24 | Equivalent decimal/time representations count as identical normalized content |
| TC25 | Corrected request can reuse an ID rejected before posting |
| TC26 | Fractional 0.125 KG is stored exactly |
| TC27 | Receipt/reversal original-reference contract enforced |
| TC28 | Oversized payload rejected and audited |

Run `python run_demo.py` from the project root. Tests use isolated temporary databases. Demo evidence uses a separate fresh database and does not reset a user's CLI database. Fault injection and the negative-stock fixture are test techniques, not production features or observed incidents.

## Manual UAT scripts: execution and sign-off pending

The following are proposed business scripts. All **actual result**, **tester**, **date** and **approval** fields are pending.

| ID / role | Preconditions and steps | Expected business result | Requirements | Actual |
|---|---|---|---|---|
| UAT01 Receiving | Fresh demo; submit examples/valid_receipt.json; inspect reference/balances | POSTED; 25 EA added to correct PO line and MAIN/MAT100 | FR02/03/06/08 | Not executed |
| UAT02 WMS owner | Resubmit UAT01 exactly after an uncertain acknowledgement | DUPLICATE, original reference, no extra stock | FR04/07/11 | Not executed |
| UAT03 Buyer | Change quantity to 30 while reusing accepted key | Conflict; buyer sees no overwritten transaction | FR04/11 | Not executed |
| UAT04 Receiving | Use a new ID with unknown PO or wrong UOM; correct it afterward | Actionable rejection; corrected rejected key may post | FR01/02/04/11 | Not executed |
| UAT05 Inventory | After UAT01, submit full_reversal.json; retry it | One reversal, balances restored, duplicate retry safe | FR05/06/08 | Not executed |
| UAT06 Receiving | Post distinct 25 and 75 receipts to fresh 100-unit line; submit another unit | First two post; over-receipt rejected | FR03 | Not executed |
| UAT07 Support | Review injected technical-failure evidence and retries | No partial business update; traceable failed attempt and subsequent success | FR06/07/08/11 | Not executed |
| UAT08 Business owner | Review MAIN-only baseline and proposed multi-warehouse change | Scope understood; no implicit approval of deferred expansion | FR10, CR001 | Not executed |

UAT participants must confirm whether these rules match their actual business needs; executing a scripted example is not enough if the requirement itself is wrong.

## Defect and sign-off templates

**Defect:** ID; requirement/test; environment/build; preconditions; steps; expected; actual; evidence; severity; business impact; owner; workaround; retest result; closure decision.

**Sign-off:** baseline version; executed UAT IDs; unresolved defects/risks; accepting business owner; QA recommendation; decision (accept/conditional/reject); date. No real signatures or client approvals are supplied.

## Pending integration tests

- Run SQL Server smoke assertions on a new database, then reproduce the reference business cases through the target adapter.
- Test same-key and different-key concurrency, lock contention, deadlock victim retry, connection loss before and after commit, and crash/restart durability.
- Verify stock/PO reconciliation with actual opening balances and every in-scope movement type; the zero-opening demo is not a complete ERP inventory model.
- Test authentication, authorization, transport failures, restricted procedure execution, rate/size limits, redaction, alerting and audit-store failure recovery.
- Set realistic workloads and response targets with stakeholders before load testing. Record environment and actual results rather than inferring throughput from unit-test duration.
