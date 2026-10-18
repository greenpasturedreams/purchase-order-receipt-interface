-- Internal core procedure, called ONLY after JSON contract validation by an adapter.
-- Python/SQLite is the executed reference. SQL Server runtime/parity testing is pending.
-- Parameters are normalized ASCII IDs, integer line/version, positive decimal string,
-- UTC datetime2(3), and original request text. Auth and strict JSON parsing are adapter duties.
CREATE OR ALTER PROCEDURE dbo.ProcessReceipt
 @SourceSystem varchar(40),@ReceiptId varchar(40),@ActionCode varchar(8),
 @PoNumber varchar(40),@LineNumber int,@QuantityText varchar(40),@Uom varchar(40),
 @WarehouseCode varchar(40),@ReceivedAtUtc datetime2(3),@OriginalReceiptId varchar(40)=NULL,
 @SchemaVersion int=1,@RequestPayload nvarchar(max)=N'{}',@AsOfUtc datetime2(3)=NULL,
 @InjectFailure bit=0
AS
BEGIN
 SET NOCOUNT ON;
 SET XACT_ABORT ON;
 IF @@TRANCOUNT<>0 THROW 51000,'Invoke without an ambient transaction.',1;
 IF @AsOfUtc IS NULL SET @AsOfUtc=SYSUTCDATETIME();
 DECLARE @AttemptId bigint,@Quantity decimal(18,3),@Canonical varchar(600),@Hash binary(32),@Prior binary(32),
 @Outcome varchar(20)='POSTED',@Code varchar(40)=NULL,@Http int=201,@Reference varchar(81)=NULL,
 @Material varchar(40),@PoUom varchar(40),@Status varchar(6),@Created datetime2(3),
 @Ordered decimal(18,3),@Received decimal(18,3),@OnHand decimal(18,3),@Delta decimal(18,3),
 @OriginalAction varchar(8),@OriginalPo varchar(40),@OriginalLine int,@OriginalUom varchar(40),
 @OriginalWarehouse varchar(40),@OriginalQty decimal(18,3),@OriginalTime datetime2(3),@Stamp varchar(24);
 INSERT dbo.InterfaceAttempt(SourceSystem,ReceiptId,RequestAtUtc,RequestPayload,OutcomeCode)
 VALUES(@SourceSystem,@ReceiptId,@AsOfUtc,@RequestPayload,'RECEIVED');
 SET @AttemptId=SCOPE_IDENTITY();
 BEGIN TRY
  -- Do not rely on decimal conversion alone: SQL Server may round excess precision.
  IF @QuantityText IS NULL OR @QuantityText='' OR @QuantityText COLLATE Latin1_General_100_BIN2 LIKE '%[^0-9.]%'
   OR LEN(@QuantityText)-LEN(REPLACE(@QuantityText,'.',''))>1
   OR LEFT(@QuantityText,1)='.' OR RIGHT(@QuantityText,1)='.'
   OR (CHARINDEX('.',@QuantityText)>0 AND LEN(@QuantityText)-CHARINDEX('.',@QuantityText)>3)
   OR (CASE WHEN CHARINDEX('.',@QuantityText)=0 THEN LEN(@QuantityText) ELSE CHARINDEX('.',@QuantityText)-1 END)>15
  BEGIN SET @Code='INVALID_QUANTITY';GOTO RejectRequest; END;
  SET @Quantity=TRY_CONVERT(decimal(18,3),@QuantityText);
  IF @Quantity IS NULL OR @Quantity<=0 BEGIN SET @Code='INVALID_QUANTITY';GOTO RejectRequest; END;
  IF @SchemaVersion IS NULL OR @SchemaVersion<>1 OR @LineNumber IS NULL OR @LineNumber<=0
   OR @SourceSystem IS NULL OR @ReceiptId IS NULL OR @PoNumber IS NULL OR @Uom IS NULL OR @WarehouseCode IS NULL
   OR @SourceSystem='' OR @ReceiptId='' OR @PoNumber='' OR @Uom='' OR @WarehouseCode=''
   OR @ActionCode IS NULL OR @ActionCode NOT IN ('RECEIPT','REVERSAL')
   OR (@ActionCode='RECEIPT' AND @OriginalReceiptId IS NOT NULL)
   OR (@ActionCode='REVERSAL' AND (@OriginalReceiptId IS NULL OR @OriginalReceiptId=''))
  BEGIN SET @Code='SCHEMA_ERROR';SET @Http=400;GOTO RejectRequest; END;
  IF @ReceivedAtUtc IS NULL BEGIN SET @Code='INVALID_TIMESTAMP';SET @Http=400;GOTO RejectRequest; END;
  IF @ReceivedAtUtc>DATEADD(minute,5,@AsOfUtc) BEGIN SET @Code='FUTURE_TIMESTAMP';GOTO RejectRequest; END;
  IF @SourceSystem<>'WMS_DEMO' BEGIN SET @Code='UNKNOWN_SOURCE';GOTO RejectRequest; END;
  IF @WarehouseCode<>'MAIN' BEGIN SET @Code='UNSUPPORTED_WAREHOUSE';GOTO RejectRequest; END;
  SET @Stamp=CONCAT(CONVERT(char(19),@ReceivedAtUtc,126),'.',
    RIGHT('00'+CONVERT(varchar(3),DATEPART(millisecond,@ReceivedAtUtc)),3),'Z');
  SET @Canonical=CONCAT('1|',@SourceSystem,'|',@ReceiptId,'|',@ActionCode,'|',@PoNumber,'|',
    CONVERT(varchar(10),@LineNumber),'|',CONVERT(varchar(40),@Quantity),'|',@Uom,'|',@WarehouseCode,'|',
    @Stamp,'|',COALESCE(@OriginalReceiptId,''));
  SET @Hash=HASHBYTES('SHA2_256',@Canonical);
  BEGIN TRANSACTION;
  SELECT @Prior=PayloadHash FROM dbo.ReceiptLedger WITH(UPDLOCK,HOLDLOCK)
   WHERE SourceSystem=@SourceSystem AND ReceiptId=@ReceiptId;
  IF @Prior IS NOT NULL
  BEGIN
   IF @Prior<>@Hash BEGIN SET @Code='IDEMPOTENCY_CONFLICT';SET @Http=409;GOTO RejectRequest; END;
   SET @Outcome='DUPLICATE';SET @Http=200;GOTO CommitRequest;
  END;
  SELECT @Material=MaterialId,@PoUom=Uom,@Status=LineStatus,@Created=CreatedAtUtc,
   @Ordered=OrderedQuantity,@Received=ReceivedQuantity
  FROM dbo.PurchaseOrderLine WITH(UPDLOCK,HOLDLOCK) WHERE PoNumber=@PoNumber AND LineNumber=@LineNumber;
  IF @Material IS NULL BEGIN SET @Code='UNKNOWN_PO_LINE';GOTO RejectRequest; END;
  IF @Uom<>@PoUom BEGIN SET @Code='UOM_MISMATCH';GOTO RejectRequest; END;
  IF @ReceivedAtUtc<@Created BEGIN SET @Code='BEFORE_PO_CREATION';GOTO RejectRequest; END;
  IF @ActionCode='RECEIPT'
  BEGIN
   IF @Status<>'OPEN' BEGIN SET @Code='PO_LINE_CLOSED';GOTO RejectRequest; END;
   IF @Received+@Quantity>@Ordered BEGIN SET @Code='OVER_RECEIPT';GOTO RejectRequest; END;
   SET @Delta=@Quantity;
  END
  ELSE
  BEGIN
   SELECT @OriginalAction=ActionCode,@OriginalPo=PoNumber,@OriginalLine=LineNumber,@OriginalUom=Uom,
    @OriginalWarehouse=WarehouseCode,@OriginalQty=Quantity,@OriginalTime=ReceivedAtUtc
   FROM dbo.ReceiptLedger WITH(UPDLOCK,HOLDLOCK)
   WHERE SourceSystem=@SourceSystem AND ReceiptId=@OriginalReceiptId;
   IF @OriginalAction IS NULL OR @OriginalAction<>'RECEIPT' BEGIN SET @Code='ORIGINAL_NOT_FOUND';GOTO RejectRequest; END;
   IF @OriginalPo<>@PoNumber OR @OriginalLine<>@LineNumber OR @OriginalUom<>@Uom OR @OriginalWarehouse<>@WarehouseCode
   BEGIN SET @Code='REVERSAL_REFERENCE_MISMATCH';GOTO RejectRequest; END;
   IF EXISTS(SELECT 1 FROM dbo.ReceiptLedger WITH(UPDLOCK,HOLDLOCK)
     WHERE SourceSystem=@SourceSystem AND OriginalReceiptId=@OriginalReceiptId AND ActionCode='REVERSAL')
   BEGIN SET @Code='ALREADY_REVERSED';SET @Http=409;GOTO RejectRequest; END;
   IF @Quantity<>@OriginalQty BEGIN SET @Code='REVERSAL_QUANTITY';GOTO RejectRequest; END;
   IF @ReceivedAtUtc<@OriginalTime BEGIN SET @Code='REVERSAL_TIMESTAMP';GOTO RejectRequest; END;
   SET @Delta=-@Quantity;
  END;
  SELECT @OnHand=OnHandQuantity FROM dbo.InventoryBalance WITH(UPDLOCK,HOLDLOCK)
    WHERE WarehouseCode=@WarehouseCode AND MaterialId=@Material;
  IF @OnHand IS NULL BEGIN SET @Code='INVENTORY_NOT_CONFIGURED';GOTO RejectRequest; END;
  IF @OnHand+@Delta<0 OR @Received+@Delta<0 BEGIN SET @Code='NEGATIVE_BALANCE';GOTO RejectRequest; END;
  INSERT dbo.ReceiptLedger VALUES(@SourceSystem,@ReceiptId,@ActionCode,@PoNumber,@LineNumber,
    @Quantity,@Delta,@Uom,@WarehouseCode,@ReceivedAtUtc,@OriginalReceiptId,@Hash);
  IF @InjectFailure=1 THROW 51001,'Demonstration fault after ledger insert.',1;
  UPDATE dbo.PurchaseOrderLine SET ReceivedQuantity=ReceivedQuantity+@Delta
    WHERE PoNumber=@PoNumber AND LineNumber=@LineNumber;
  UPDATE dbo.InventoryBalance SET OnHandQuantity=OnHandQuantity+@Delta
    WHERE WarehouseCode=@WarehouseCode AND MaterialId=@Material;
CommitRequest:
  SET @Reference=CONCAT(@SourceSystem,'/',@ReceiptId);
  UPDATE dbo.InterfaceAttempt SET OutcomeCode=@Outcome,ErrorCode=NULL,HttpStatus=@Http,
    ProcessingReference=@Reference WHERE AttemptId=@AttemptId;
  COMMIT TRANSACTION;
  GOTO ReturnResult;
RejectRequest:
  IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
  IF @Http=201 SET @Http=422;
  SET @Outcome='REJECTED';
  UPDATE dbo.InterfaceAttempt SET OutcomeCode=@Outcome,ErrorCode=@Code,HttpStatus=@Http
    WHERE AttemptId=@AttemptId;
ReturnResult:
  SELECT @Outcome outcome,@Http http_status,@Reference processing_reference,@Code error_code,@AttemptId attempt_id;
 END TRY
 BEGIN CATCH
  IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
  UPDATE dbo.InterfaceAttempt SET OutcomeCode='TECHNICAL_ERROR',ErrorCode='TECHNICAL_ERROR',HttpStatus=503,
    ProcessingReference=NULL WHERE AttemptId=@AttemptId;
  SELECT 'TECHNICAL_ERROR' outcome,503 http_status,CAST(NULL AS varchar(81)) processing_reference,
    'TECHNICAL_ERROR' error_code,@AttemptId attempt_id;
 END CATCH;
END;
GO
