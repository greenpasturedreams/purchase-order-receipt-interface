# Processes and system boundaries

## Assumed current state: validate through elicitation

This diagram is an illustrative manual workflow, not an observed or measured company process.

```mermaid
flowchart TD
 A[Warehouse records receipt] --> B[Receipt details sent to receiving team]
 B --> C[Clerk finds purchase-order line]
 C --> D{PO and quantity valid?}
 D -- No --> E[Buyer and receiving investigate]
 E --> B
 D -- Yes --> F[Clerk records receipt in purchasing system]
 F --> G[PO and stock updated]
 G --> H[Manual reconciliation]
 B -. Response unclear or file resent .-> I[Possible repeated manual entry]
 I --> C
```

## Proposed future state

```mermaid
flowchart TD
 A[WMS submits receipt JSON] --> B[Adapter validates schema and identity]
 B --> C{Valid contract?}
 C -- No --> R[Return actionable rejection and audit attempt]
 C -- Yes --> D[Start protected posting transaction]
 D --> E{Successful business key exists?}
 E -- Same normalized payload --> F[Return original reference as duplicate]
 E -- Different payload --> G[Return conflict for review]
 E -- No --> H[Validate PO line, units, quantity and reversal rules]
 H --> I{Business rules satisfied?}
 I -- No --> R
 I -- Yes --> J[Write receipt ledger and update PO plus stock]
 J --> K{Transaction succeeds?}
 K -- Yes --> L[Commit success audit and business writes]
 K -- No --> M[Rollback all business writes and audit technical failure]
 M --> N[Sender may retry identical request]
 G --> R
 F --> O[Audit duplicate without extra stock movement]
 L --> P[Return posted reference]
```

## Proposed system context vs implemented example

```mermaid
flowchart LR
 W[External WMS: proposed integration] --> A[Authenticated adapter: design only]
 A --> S[SQL Server core procedure: supplied, engine validation pending]
 S --> P[(PO lines)]
 S --> L[(Receipt ledger)]
 S --> I[(Inventory balances)]
 S --> E[(Interface attempts)]
 C[Local CLI: implemented] --> R[Python reference processor]
 R --> D[(SQLite demo database)]
```

The local CLI demonstrates request processing; it is not a deployed endpoint or authentication service. SQL Server scripts implement the proposed core posting model behind an adapter. Do not substitute SQLite test results for SQL Server transaction or performance evidence.

## Transaction sequence and lost-response retry

```mermaid
sequenceDiagram
 participant W as Sender
 participant A as Adapter or reference processor
 participant D as Purchasing database
 W->>A: Receipt key plus business payload
 A->>A: Validate and normalize
 A->>D: Begin transaction and check successful key
 D-->>A: No prior successful posting
 A->>D: Validate and write ledger, PO balance, stock and audit
 A->>D: Commit
 A--xW: Response lost after commit
 W->>A: Identical retry
 A->>D: Check same successful key and payload hash
 D-->>A: Original processing reference
 A->>D: Audit duplicate without additional business balance changes
 A-->>W: DUPLICATE plus original reference
```

## Relational model

```mermaid
erDiagram
 PURCHASE_ORDER_LINE ||--o{ RECEIPT_LEDGER : records
 PURCHASE_ORDER_LINE {
  string po_number PK
  int line_number PK
  string material_id
  decimal ordered_quantity
  decimal received_quantity
 }
 RECEIPT_LEDGER {
  string source_system PK
  string receipt_id PK
  string action
  decimal quantity
  decimal delta_quantity
  string original_receipt_id
  string payload_hash
 }
 INVENTORY_BALANCE {
  string warehouse PK
  string material_id PK
  decimal on_hand_quantity
 }
 INTERFACE_ATTEMPT {
  int attempt_id PK
  string source_system
  string receipt_id
  string outcome
  string error_code
 }
```

An attempt may be malformed or rejected, so it need not have a successful ledger parent. Reversal references are validated against the original receipt by business logic. Inventory is related by warehouse/material through the PO line. Posting is all-or-nothing across ledger and balances; failed-attempt logging occurs after rollback. If the audit store itself is unavailable, production telemetry/reconciliation must detect the failure; that recovery integration is pending.
