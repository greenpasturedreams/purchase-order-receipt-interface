# Delivery, stakeholder and communication pack

This pack contains illustrative plans and communication templates. No meetings were held, messages sent, external staff assigned, deadlines committed or customer approvals obtained as part of this case study.

## Proposed SDLC and milestones

| Phase | Indicative window | Deliverable / exit gate | Proposed owner |
|---|---|---|---|
| Discovery | Week 1 | Validate receipt process, objectives, field meanings and assumptions | BA + business owner |
| Requirements | Week 2 | Reviewed BRD, scope, acceptance criteria, mappings and traceability | BA + architect + QA |
| Design/build | Weeks 3–4 | Approved adapter/DB design and target-engine implementation | Architect + developers |
| Integration testing | Week 5 | Functional/concurrency/recovery/security evidence, reconciliation | QA + integration/support |
| UAT/training | Week 6 | Business acceptance, training and operational readiness | Business UAT lead + trainer |
| Release/hypercare | After go/no-go | Controlled rollout, support ownership and monitored reconciliation | PM + sponsor + support |

The windows are planning placeholders. Scope, team capacity, environment readiness and estimates must be confirmed before setting dates. The local reference is already implemented; it does not mean the remaining integration phases are complete.

## RACI

R = responsible, A = accountable, C = consulted, I = informed. Roles are proposed.

| Activity | Business owner | BA | Architect/dev | QA | PM | Support/trainer |
|---|---|---|---|---|---|---|
| Confirm business requirements | A | R | C | C | I | C |
| Technical design/build | C | C | A/R | C | I | C |
| Requirements traceability | C | A/R | C | R | I | I |
| Integration testing | C | C | R | A/R | I | C |
| Business acceptance | A/R | C | C | R | I | C |
| Schedule/dependency coordination | C | R | C | C | A | C |
| User training | A | C | C | C | I | R |
| Go/no-go | A | C | C | C | R | C |

## Dependency and issue register

| ID | Dependency / risk | Impact | Proposed mitigation / owner | Current state |
|---|---|---|---|---|
| DEP01 | Target SQL Server instance and validating adapter unavailable | Engine/runtime behavior not confirmed | Provision isolated environment; architect/dev | Open |
| DEP02 | Source receipt ID and reversal conventions unconfirmed | Retry/correction semantics could conflict with WMS | Elicit with source owner; BA | Open |
| R01 | SQLite evidence mistaken for target-engine certification | Inaccurate release readiness | Separate reference and SQL Server test status; QA | Documented |
| R02 | Business allows over-receipt tolerance or partial reversals | Baseline may not fit operations | Confirm rules; raise scoped change; business owner | Open |
| R03 | Lost acknowledgement or deadlock triggers unsafe retries | Duplicate or missing postings if contract ignored | Stable IDs, idempotency, target-engine recovery tests; integration lead | Reference covered, integration pending |
| R04 | Audit database unavailable | Missing operational visibility | Define external telemetry, alerting and reconciliation recovery; support | Design pending |

Escalate blocked dependencies or proposed scope changes to the PM/business owner with impact and options. Do not silently expand scope or claim that examples establish business approval.

## Sample elicitation meeting agenda

**Purpose:** confirm what constitutes a receipt and how duplicates/corrections should behave.

1. Review current process and agree which steps are assumptions.
2. Walk through partial receipt, lost acknowledgement, wrong PO/UOM and reversal examples.
3. Confirm identifiers, quantity precision, timestamp meaning and permitted locations.
4. Agree exception ownership and retry rules.
5. Record open decisions, evidence needed and accountable roles.

**Meeting notes template:** date, participants, baseline reviewed, decision ID, options, decision/rationale, owner, due date and unresolved questions. Do not populate a decision as approved without actual confirmation.

## Sample status report: case-study build

**Overall:** reference demonstration ready for review; production integration not release-ready.

**Completed:** BRD, process diagrams, contract/mapping, functional requirements, traceability, reference processor, 28 passing reference tests, demonstration reconciliation, SQL Server core/smoke scripts and training/UAT packs.

**Open:** actual stakeholder elicitation and baseline approval; SQL Server deployment/parity/concurrency tests; authenticated adapter; security, load, recovery and operational readiness; business UAT/sign-off.

**Decision needed:** confirm the baseline rules and target environment before estimating integration work. CR001 multi-warehouse remains proposed and unimplemented.

## Sample technical/nontechnical communication

**For receiving:** “A duplicate response acknowledges the original receipt. Do not create a new receipt ID solely because the first response was lost; that could turn a retry into a second business transaction.”

**For developers:** “Enforce the successful source/receipt key and normalized payload comparison inside the posting transaction. Database uniqueness alone cannot distinguish a valid retry from conflicting content.”

## Training/webinar outline

Proposed 20-minute session: five minutes on statuses and stable IDs, five on partial receipts and corrections, five on exception examples, five on Q&A and a knowledge check. Trainer/business owner should review content and accessibility before delivery. No webinar has been delivered or attendance recorded.
