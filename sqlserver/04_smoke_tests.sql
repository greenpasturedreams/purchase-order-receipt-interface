-- NOT EXECUTED in this project. Run in the new demo DB after 01 and 02, once.
-- Do not use production data. Each procedure call manages its own transaction.
SET NOCOUNT ON;
EXEC dbo.ProcessReceipt 'WMS_DEMO','RCPT0001','RECEIPT','PO1001',1,'25.000','EA','MAIN',
 '2026-10-18T10:00:00',NULL,1,N'{"example":"normalized receipt"}','2026-10-18T12:00:00';
EXEC dbo.ProcessReceipt 'WMS_DEMO','RCPT0001','RECEIPT','PO1001',1,'25','EA','MAIN',
 '2026-10-18T10:00:00',NULL,1,N'{"example":"retry"}','2026-10-18T12:00:00';
IF (SELECT COUNT(*) FROM dbo.ReceiptLedger)<>1 THROW 51010,'Duplicate posting detected.',1;
IF (SELECT ReceivedQuantity FROM dbo.PurchaseOrderLine WHERE PoNumber='PO1001' AND LineNumber=1)<>25
 THROW 51011,'PO balance mismatch.',1;
IF (SELECT PayloadHash FROM dbo.ReceiptLedger WHERE ReceiptId='RCPT0001' AND SourceSystem='WMS_DEMO')
 <>CONVERT(binary(32),'7ae6d4ea48edf21f68ef2ac314d81e2572b30f536b6ad350afd374836fd8fdca',2)
 THROW 51012,'Canonical hash differs from reference.',1;
EXEC dbo.ProcessReceipt 'WMS_DEMO','RCPT0001','RECEIPT','PO1001',1,'30','EA','MAIN',
 '2026-10-18T10:00:00',NULL,1,N'{"example":"conflict"}','2026-10-18T12:00:00';
IF NOT EXISTS(SELECT 1 FROM dbo.InterfaceAttempt WHERE ErrorCode='IDEMPOTENCY_CONFLICT')
 THROW 51013,'Conflict not detected.',1;
EXEC dbo.ProcessReceipt 'WMS_DEMO','ROLLBACK1','RECEIPT','PO1001',1,'5','EA','MAIN',
 '2026-10-18T10:00:00',NULL,1,N'{"example":"fault"}','2026-10-18T12:00:00',1;
IF EXISTS(SELECT 1 FROM dbo.ReceiptLedger WHERE ReceiptId='ROLLBACK1') THROW 51014,'Rollback failed.',1;
EXEC dbo.ProcessReceipt 'WMS_DEMO','REV0001','REVERSAL','PO1001',1,'25','EA','MAIN',
 '2026-10-18T11:00:00','RCPT0001',1,N'{"example":"reversal"}','2026-10-18T12:00:00';
IF (SELECT SUM(DeltaQuantity) FROM dbo.ReceiptLedger)<>0 THROW 51015,'Reversal mismatch.',1;
IF (SELECT ReceivedQuantity FROM dbo.PurchaseOrderLine WHERE PoNumber='PO1001' AND LineNumber=1)<>0
 THROW 51016,'PO reversal balance mismatch.',1;
IF (SELECT OnHandQuantity FROM dbo.InventoryBalance WHERE MaterialId='MAT100' AND WarehouseCode='MAIN')<>0
 THROW 51017,'Inventory reversal balance mismatch.',1;
SELECT 'Smoke assertions passed on this SQL Server instance' result;
