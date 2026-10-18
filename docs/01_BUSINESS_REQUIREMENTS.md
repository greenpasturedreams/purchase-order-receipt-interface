# Business requirements document

**Project:** Purchase Order and Goods Receipt Interface. **Version:** 1.0 proposed baseline. **Prepared:** October 18, 2026. **Approval:** Not submitted for business approval.

This is an independent Business Analyst case study with fictional demonstration records. The process assumptions and stakeholder roles below are proposed for elicitation; they do not describe a confirmed employer implementation or completed client engagement.

## Business problem and decision

A purchasing team needs reliable transfer of goods-receipt information from an external warehouse system into its purchasing database. Retries, partial receipts and corrections can cause confusion when a response is lost or the same identifier is submitted with different data. The business needs a decision on scope, rules and exception ownership before developers implement the interface.

The earlier purchasing analytics project motivates questions about receipt recording and process visibility. Its anonymized event log is not an integration source and does not establish that this proposed interface would improve a real company's performance.

## Business objectives

| ID | Objective | Proposed success measure | Baseline / owner |
|---|---|---|---|
| BR01 | Prevent duplicate stock and PO updates from retries | Zero additional business postings for an identical accepted-key retry in acceptance tests | Production baseline unknown; receiving lead |
| BR02 | Maintain correct PO and inventory balances | Zero reconciliation differences for the scoped receipt/reversal transactions | Existing adjustment/movement baseline to be collected; inventory control |
| BR03 | Make exceptions understandable and traceable | Each processed local attempt has a status, code and correlation reference where applicable | Current manual process to be validated; application support |
| BR04 | Make interface changes testable and controlled | Every baseline functional requirement mapped to acceptance criteria and tests | BA / QA lead |

No production time savings, cost reduction, ROI or user acceptance has been measured. A business pilot should establish current receipt-posting effort, duplication rate, exception aging and reconciliation effort before evaluating improvement.

## Scope baseline

**In scope:** one registered source (`WMS_DEMO`), one warehouse (`MAIN`), existing PO line/master data, positive receipt quantities to three decimal places, partial receipts, exact retries, conflicts, full reversals, atomic balance updates, local audit trail, source-to-target queries, proposed JSON contract, test plan and training content.

**Out of scope:** a deployed HTTP endpoint, ERP/WMS connection, authentication implementation, purchase-order creation, pricing and accounting, invoice matching, unit conversions, receiving inspections, stock consumption, automatic PO closure, partial reversals, multiple warehouses, production monitoring and signed business UAT. SQL Server core scripts are supplied but not engine-tested in this environment.

## Users and responsibilities

| Role | Need / proposed responsibility |
|---|---|
| Receiving clerk | Understand accepted, duplicate and rejected outcomes; correct source data |
| Purchasing buyer | Confirm line status and remaining ordered quantity; resolve PO exceptions |
| Inventory controller | Review reversals and balance reconciliation |
| External-system owner | Supply stable receipt IDs and retry rules; preserve original transaction references |
| Application support | Investigate technical failures and unresolved attempts |
| Architect / developers | Implement approved transport, transaction and deployment design |
| QA / business UAT lead | Verify requirements and obtain business acceptance evidence |
| Sponsor / PM | Confirm scope, priorities, dependencies and go/no-go authority |

These are case-study role assignments, not actual named participants or commitments.

## Key business rules

- The source system plus receipt ID identifies one successful business submission. A retry with the same normalized payload returns the original reference and changes no balances.
- A posted key with different normalized business data is a conflict; it is not silently overwritten.
- Rejected keys are not reserved forever. A corrected request can reuse a previously rejected key because no successful posting exists.
- Several receipts with different receipt IDs may fill a PO line. Total net received quantity must remain between zero and the ordered quantity; version 1 has no over-receipt tolerance.
- A full reversal uses a new receipt ID and references one original receipt from the same source. It must match PO line, warehouse, UOM and original quantity. It can occur only once, cannot predate the original, and cannot create negative balances.
- New receipts require an open PO line. A reversal of a valid original receipt is allowed after the line closes so corrections are not blocked by ordinary closure.
- Corrective changes are new ledger events, not edits to posted records. Partial reversals are deferred.
- No UOM conversion is inferred. Values use decimal quantities, not binary floating-point arithmetic.

## Assumptions, dependencies and questions for elicitation

| Item | Proposed position | Confirmation needed |
|---|---|---|
| ID ownership | WMS supplies durable IDs unique within its source namespace | What happens after WMS restore/replay? |
| Receipt timing | UTC physical/event timestamp, to millisecond precision | Is arrival, inspection or posting time the correct field? |
| Master data | PO lines and material/UOM records already exist | Which system owns changes and how quickly are they replicated? |
| Quantities | Three decimal places; no over-receipt tolerance | Are some materials integer-only? Is tolerance needed? |
| Corrections | Full reversal followed by a new corrected receipt | Who can authorize reversal when stock has been consumed? |
| Technical retry | Identical payload after transient failure or lost response | Who owns retries and how are unresolved transactions reconciled? |
| Cutover | Sample replay and reconciliation before production enablement | What opening balances and in-flight messages must be accounted for? |

## Acceptance and approval gates

Reference demo tests are evidence of implemented example behavior only. The business baseline, live transport/security, SQL Server integration, load/recovery tests, production data reconciliation, user training and UAT sign-off remain separate gates. No sample approval below should be treated as authorization to deploy.

**Proposed sign-off record:** requirement baseline/version; business owner; QA owner; unresolved issues; decision; decision date. All actual approval fields are pending.
