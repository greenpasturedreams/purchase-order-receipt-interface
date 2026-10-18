# Change request CR001: additional warehouses

**Status:** Proposed, decision pending. **Baseline affected:** v1 MAIN-only interface. **Requester:** illustrative receiving operations role. **Priority and funding:** unapproved. **Implemented:** No.

## Business request

Allow a second warehouse to submit receipts so inventory can be recorded at the correct location without a manual transfer. The existing `warehouse` payload field is present, but v1 accepts MAIN only. A second value currently returns UNSUPPORTED_WAREHOUSE; do not describe this request as already delivered.

## Options

| Option | Benefits | Costs / risks |
|---|---|---|
| Defer to next controlled release | Preserves approved scope and test focus | Business may retain manual handling for new site |
| Extend warehouse configuration and source permissions | Reuses existing composite stock key and request field | Requires master data, authorization, revised rules, migration and testing |
| Remove warehouse validation | Minimal apparent coding | Not recommended: unknown locations could corrupt stock allocation |

**Recommendation:** define the warehouse/source authorization and PO receiving-location rules first, then estimate and approve a controlled extension. No sponsor decision has been made.

## Impact assessment

| Area | Required change |
|---|---|
| Requirements | Revise FR10; define allowed sites per source and permitted PO receiving locations |
| Contract/versioning | Existing field can carry the value; agree capability/version rollout and compatibility before changing accepted values |
| Data | Add warehouse master/source authorization configuration; seed material/site balances and migration reconciliation |
| Business key | Keep source + receipt ID globally unique within source; warehouse stays part of payload hash, so changing a posted request's warehouse must remain a conflict |
| Posting | Lock and update the correct warehouse/material balance; no cross-warehouse reversal |
| Security | Bind allowed warehouses to authenticated source identity; no trust in payload alone |
| Tests | MAIN regression, second warehouse, unknown/unauthorized site, same receipt ID across sites, wrong-site reversal and concurrent site postings |
| Reporting | Reconcile quantities by warehouse and material; partition exception views appropriately |
| Training | Explain site selection, new rejection messages, escalation and correction routes |
| Delivery | Architect/developer/QA/business estimates needed; schedule/funding not committed |

## Proposed additional acceptance criteria

- An authorized receipt updates only the specified configured warehouse balance.
- An unauthorized site returns rejection and changes no balances.
- The same source/receipt key with a different warehouse returns conflict.
- A reversal cannot move stock across warehouses.
- Existing MAIN behavior and all prior regression tests still pass.

**Decision log template:** approver, decision date, scope/version, estimate, implementation owner, rollout dependencies and training/UAT changes. Leave pending until an actual review occurs.
