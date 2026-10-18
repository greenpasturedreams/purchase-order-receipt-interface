-- Run in a NEW, EMPTY demonstration database. Does not create/drop a database.
-- SQL Server 2016 SP1+; use a currently supported engine for deployment validation.
-- This implementation has not been executed against SQL Server in this project.
SET XACT_ABORT ON;
GO
CREATE TABLE dbo.PurchaseOrderLine (
 PoNumber varchar(40) COLLATE Latin1_General_100_BIN2 NOT NULL,
 LineNumber int NOT NULL,MaterialId varchar(40) NOT NULL,Uom varchar(40) NOT NULL,
 LineStatus varchar(6) NOT NULL,CreatedAtUtc datetime2(3) NOT NULL,
 OrderedQuantity decimal(18,3) NOT NULL,ReceivedQuantity decimal(18,3) NOT NULL DEFAULT(0),
 CONSTRAINT PK_PurchaseOrderLine PRIMARY KEY(PoNumber,LineNumber),
 CONSTRAINT CK_PoQuantity CHECK(OrderedQuantity>0 AND ReceivedQuantity>=0 AND ReceivedQuantity<=OrderedQuantity),
 CONSTRAINT CK_PoStatus CHECK(LineStatus IN ('OPEN','CLOSED')));
CREATE TABLE dbo.InventoryBalance (
 WarehouseCode varchar(40) COLLATE Latin1_General_100_BIN2 NOT NULL,
 MaterialId varchar(40) NOT NULL,OnHandQuantity decimal(18,3) NOT NULL,
 CONSTRAINT PK_InventoryBalance PRIMARY KEY(WarehouseCode,MaterialId),
 CONSTRAINT CK_InventoryQuantity CHECK(OnHandQuantity>=0));
CREATE TABLE dbo.ReceiptLedger (
 SourceSystem varchar(40) COLLATE Latin1_General_100_BIN2 NOT NULL,
 ReceiptId varchar(40) COLLATE Latin1_General_100_BIN2 NOT NULL,
 ActionCode varchar(8) NOT NULL,PoNumber varchar(40) COLLATE Latin1_General_100_BIN2 NOT NULL,
 LineNumber int NOT NULL,Quantity decimal(18,3) NOT NULL,DeltaQuantity decimal(18,3) NOT NULL,
 Uom varchar(40) NOT NULL,WarehouseCode varchar(40) NOT NULL,ReceivedAtUtc datetime2(3) NOT NULL,
 OriginalReceiptId varchar(40) COLLATE Latin1_General_100_BIN2 NULL,PayloadHash binary(32) NOT NULL,
 CONSTRAINT PK_ReceiptLedger PRIMARY KEY(SourceSystem,ReceiptId),
 CONSTRAINT FK_ReceiptPo FOREIGN KEY(PoNumber,LineNumber) REFERENCES dbo.PurchaseOrderLine(PoNumber,LineNumber),
 CONSTRAINT CK_ReceiptAction CHECK(ActionCode IN ('RECEIPT','REVERSAL')),
 CONSTRAINT CK_ReceiptPositive CHECK(Quantity>0),
 CONSTRAINT CK_ReceiptDelta CHECK((ActionCode='RECEIPT' AND DeltaQuantity=Quantity AND OriginalReceiptId IS NULL)
   OR (ActionCode='REVERSAL' AND DeltaQuantity=-Quantity AND OriginalReceiptId IS NOT NULL)));
CREATE UNIQUE INDEX UX_OneFullReversal ON dbo.ReceiptLedger(SourceSystem,OriginalReceiptId)
 WHERE ActionCode='REVERSAL';
CREATE TABLE dbo.InterfaceAttempt (
 AttemptId bigint IDENTITY PRIMARY KEY,SourceSystem varchar(40) NULL,ReceiptId varchar(40) NULL,
 RequestAtUtc datetime2(3) NOT NULL,RequestPayload nvarchar(max) NOT NULL,
 OutcomeCode varchar(20) NOT NULL,ErrorCode varchar(40) NULL,HttpStatus int NULL,
 ProcessingReference varchar(81) NULL);
GO
INSERT dbo.PurchaseOrderLine(PoNumber,LineNumber,MaterialId,Uom,LineStatus,CreatedAtUtc,OrderedQuantity)
VALUES ('PO1001',1,'MAT100','EA','OPEN','2026-10-01',100),
       ('PO1001',2,'MAT200','EA','CLOSED','2026-10-01',50),
       ('PO1002',1,'MAT300','KG','OPEN','2026-10-01',200);
INSERT dbo.InventoryBalance VALUES ('MAIN','MAT100',0),('MAIN','MAT200',0),('MAIN','MAT300',0);
GO
