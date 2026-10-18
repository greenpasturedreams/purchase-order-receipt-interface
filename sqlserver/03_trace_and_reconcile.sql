-- Source-to-target trace. Set the business key to follow the same submission.
DECLARE @Source varchar(40)='WMS_DEMO',@Receipt varchar(40)='RCPT0001';
SELECT * FROM dbo.InterfaceAttempt WHERE SourceSystem=@Source AND ReceiptId=@Receipt ORDER BY AttemptId;
SELECT * FROM dbo.ReceiptLedger WHERE SourceSystem=@Source AND ReceiptId=@Receipt;
SELECT p.* FROM dbo.PurchaseOrderLine p JOIN dbo.ReceiptLedger r
 ON p.PoNumber=r.PoNumber AND p.LineNumber=r.LineNumber
 WHERE r.SourceSystem=@Source AND r.ReceiptId=@Receipt;

-- Empty results = no discrepancies for the seeded zero-opening-balance demo.
-- A real inventory reconciliation must include opening balances and all movement types.
WITH movements AS (
 SELECT PoNumber,LineNumber,SUM(DeltaQuantity) ledger_quantity FROM dbo.ReceiptLedger GROUP BY PoNumber,LineNumber
)
SELECT p.*,COALESCE(m.ledger_quantity,0) ledger_quantity FROM dbo.PurchaseOrderLine p
LEFT JOIN movements m ON p.PoNumber=m.PoNumber AND p.LineNumber=m.LineNumber
WHERE p.ReceivedQuantity<>COALESCE(m.ledger_quantity,0);
WITH movements AS (
 SELECT r.WarehouseCode,p.MaterialId,SUM(r.DeltaQuantity) ledger_quantity
 FROM dbo.ReceiptLedger r JOIN dbo.PurchaseOrderLine p ON r.PoNumber=p.PoNumber AND r.LineNumber=p.LineNumber
 GROUP BY r.WarehouseCode,p.MaterialId
)
SELECT b.*,COALESCE(m.ledger_quantity,0) ledger_quantity FROM dbo.InventoryBalance b
LEFT JOIN movements m ON b.WarehouseCode=m.WarehouseCode AND b.MaterialId=m.MaterialId
WHERE b.OnHandQuantity<>COALESCE(m.ledger_quantity,0);
SELECT OutcomeCode,ErrorCode,COUNT(*) attempts FROM dbo.InterfaceAttempt GROUP BY OutcomeCode,ErrorCode;
