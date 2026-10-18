# Interface specification and field mapping

**Version:** proposed contract v1. **Transport proposal:** `POST /v1/receipts`, JSON over authenticated HTTPS. **Implemented transport:** local CLI only. HTTP-like statuses below are reference response fields, not proof of a running API.

## Contract

Exactly one JSON object per request, at most 16 KiB UTF-8. Unknown keys, duplicate JSON properties, missing required keys and unsupported versions are rejected. Integer fields must be JSON integers, not strings or booleans. Identifier values are case-sensitive uppercase ASCII letters, digits, underscore or hyphen, 1–40 characters; they are not silently trimmed or case-converted.

| JSON field | Type / validation | SQL Server parameter / destination |
|---|---|---|
| schema_version | Required integer 1 | @SchemaVersion; contract validation |
| source_system | Required registered ID; WMS_DEMO in demo | @SourceSystem; ReceiptLedger.SourceSystem and InterfaceAttempt |
| receipt_id | Required stable external ID | @ReceiptId; ReceiptLedger.ReceiptId; business key with source |
| action | Required RECEIPT or REVERSAL | @ActionCode; ReceiptLedger.ActionCode |
| po_number | Required ID; existing PO | @PoNumber; PurchaseOrderLine.PoNumber FK |
| line_number | Required integer 1–2147483647 | @LineNumber; PurchaseOrderLine.LineNumber FK |
| quantity | Required positive decimal **string**; 1–15 integer digits and ≤3 decimal places | @QuantityText, validated before decimal(18,3) conversion; ReceiptLedger.Quantity |
| uom | Required ID exactly matching PO line | @Uom; ReceiptLedger.Uom |
| warehouse | Required MAIN in version 1 | @WarehouseCode; inventory composite key |
| received_at | Required real UTC date/time ending Z; optional 1–3 fractional digits | Adapter parses to UTC datetime2(3); @ReceivedAtUtc; ReceiptLedger.ReceivedAtUtc |
| original_receipt_id | Required for reversal; absent/null for receipt | @OriginalReceiptId; original receipt under the same source namespace |

Timestamp must not precede PO creation or exceed the processing clock by more than five minutes. A reversal must also not predate its original receipt. A future timestamp exactly five minutes ahead is accepted. Demo clock is fixed at **2026-10-18T12:00:00Z** for repeatability; production should use an authoritative UTC clock.

## Processing precedence

1. Validate size, JSON shape, types, fields, quantity syntax and timestamp.
2. Validate registered source and supported warehouse.
3. Within the transaction, check posted source/receipt key. Same normalized content returns duplicate; different content returns conflict.
4. For a new key: locate PO line, verify UOM and event date, apply receipt or full-reversal rules, and verify stock cannot become negative.
5. Insert one ledger row and atomically update PO received quantity, inventory and success audit. Partial receipts do not automatically close a PO.

This means an identical successful retry can still succeed after the PO later closes or its original receipt is reversed. It is an acknowledgement of an existing posting, not a new business action. Errors are first-failure results in this precedence; they are not an exhaustive list of all defects in a request.

## Idempotency and normalization

Only **successful postings** reserve a business key. Corrected rejected requests can reuse their key. Reversals use new keys. A successful reversed receipt still reserves its original key.

Quantity becomes exactly three decimal places. Time becomes exactly `YYYY-MM-DDTHH:MM:SS.mmmZ`. Missing/null original receipt becomes an empty final canonical field. Field order and JSON whitespace do not matter. The canonical ASCII string is the following values joined by `|`:

`schema_version|source_system|receipt_id|action|po_number|line_number|quantity|uom|warehouse|received_at|original_receipt_id`

Identifiers cannot contain the delimiter. SHA-256 hashes the ASCII bytes. Example canonical string:

```text
1|WMS_DEMO|RCPT0001|RECEIPT|PO1001|1|25.000|EA|MAIN|2026-10-18T10:00:00.000Z|
```

Expected hash: `7ae6d4ea48edf21f68ef2ac314d81e2572b30f536b6ad350afd374836fd8fdca`.

The SQL Server core computes the same intended canonical hash. The supplied smoke assertion checks parity when executed on SQL Server; parity is not yet runtime-confirmed there.

## Responses and error handling

| Status | Outcome / code | Sender action |
|---|---|---|
| 201 | POSTED | Save processing reference; no retry required |
| 200 | DUPLICATE | Treat as acknowledgement of original successful posting |
| 409 | IDEMPOTENCY_CONFLICT | Investigate; do not overwrite posted data or blindly change ID |
| 409 | ALREADY_REVERSED | Review original reversal; do not reverse a second time |
| 400 | INVALID_JSON, SCHEMA_ERROR, INVALID_TIMESTAMP | Correct format/schema; resend |
| 413 | PAYLOAD_TOO_LARGE | Reduce payload to the documented contract |
| 422 | INVALID_QUANTITY, FUTURE_TIMESTAMP, UNKNOWN_SOURCE, UNSUPPORTED_WAREHOUSE | Correct contract/master-data issue |
| 422 | UNKNOWN_PO_LINE, PO_LINE_CLOSED, UOM_MISMATCH, BEFORE_PO_CREATION, OVER_RECEIPT | Buyer/receiving review; no business posting occurred |
| 422 | ORIGINAL_NOT_FOUND, REVERSAL_REFERENCE_MISMATCH, REVERSAL_QUANTITY, REVERSAL_TIMESTAMP | Review original receipt and correction request |
| 422 | INVENTORY_NOT_CONFIGURED, NEGATIVE_BALANCE | Inventory control investigates configuration or available stock |
| 503 | TECHNICAL_ERROR | Business writes rolled back; retry identical request after transient issue resolves |

Local response: outcome, http_status, processing_reference, error_code; rejections also include an actionable message. SQL Server adds attempt_id and returns codes; the adapter should map codes to approved user-facing messages. A client must not expose database internals.

## Storage and transaction differences

The SQLite reference stores quantities as integer thousandths, e.g. 25.125 = 25125, avoiding floating-point errors. SQL Server uses decimal(18,3). Both intend the same business arithmetic. Audit tables preserve attempts independently of successful business keys. SQLite retains the first 16,384 text characters plus a full input digest; oversized payload excerpts are not complete source records.

The reference uses BEGIN IMMEDIATE to serialize writes. SQL Server scripts use a unique successful-key constraint, a unique full-reversal constraint, UPDLOCK/HOLDLOCK around key/line checks, XACT_ABORT and TRY/CATCH. SQL Server concurrency, deadlock handling and durability must be validated on the target engine. The internal procedure requires a strictly validating adapter and no ambient transaction. Do not expose its fault-injection option or direct table writes to production clients.

## Production-only design gates

Authentication and source authorization, least-privilege execution, encrypted transport, log redaction/retention, operational alerting, rate limits, retries, load testing and disaster recovery are proposed requirements, not executed features. Business data authorization must be bound to authenticated identity, not trusted merely because the JSON says WMS_DEMO.
