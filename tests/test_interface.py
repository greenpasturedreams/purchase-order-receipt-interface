from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import sys
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from interface import AS_OF,canonical_hash,connect,initialize,normalize,process


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/'test.db'
        initialize(self.db)
        self.base=json.loads((ROOT/'examples'/'valid_receipt.json').read_text())

    def tearDown(self):
        self.tmp.cleanup()

    def send(self,**updates):
        return process(self.db,json.dumps(self.base|updates))

    def scalar(self,sql):
        with connect(self.db) as conn:
            return conn.execute(sql).fetchone()[0]

    def assert_code(self,result,code):
        self.assertEqual(result['error_code'],code)

    def test_TC01_valid_partial_receipt(self):
        self.assertEqual(self.send()['outcome'],'POSTED')
        self.assertEqual(self.scalar("SELECT received_milli FROM po_line WHERE po_number='PO1001' AND line_number=1"),25000)
        self.assertEqual(self.scalar("SELECT on_hand_milli FROM inventory WHERE material_id='MAT100'"),25000)

    def test_TC02_identical_retry_no_extra_post(self):
        first=self.send(); second=self.send()
        self.assertEqual(second['outcome'],'DUPLICATE')
        self.assertEqual(first['processing_reference'],second['processing_reference'])
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM receipt'),1)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM attempt'),2)

    def test_TC03_conflicting_resubmission(self):
        self.send()
        self.assert_code(self.send(quantity='30.000'),'IDEMPOTENCY_CONFLICT')
        self.assertEqual(self.scalar('SELECT SUM(delta_milli) FROM receipt'),25000)

    def test_TC04_unknown_po(self):
        self.assert_code(self.send(po_number='PO9999'),'UNKNOWN_PO_LINE')

    def test_TC05_unknown_line(self):
        self.assert_code(self.send(line_number=99),'UNKNOWN_PO_LINE')

    def test_TC06_closed_line(self):
        self.assert_code(self.send(line_number=2),'PO_LINE_CLOSED')

    def test_TC07_uom_mismatch(self):
        self.assert_code(self.send(uom='KG'),'UOM_MISMATCH')

    def test_TC08_bad_quantities(self):
        for q in ['0','-1','1.0001','1e2','NaN',25,'1000000000000000']:
            with self.subTest(q=q):
                self.assert_code(self.send(quantity=q),'INVALID_QUANTITY')

    def test_TC09_over_receipt(self):
        self.assert_code(self.send(quantity='100.001'),'OVER_RECEIPT')
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM receipt'),0)

    def test_TC10_multiple_partial_receipts_exact_completion(self):
        self.send(quantity='25')
        self.assertEqual(self.send(receipt_id='RCPT0002',quantity='75')['outcome'],'POSTED')
        self.assert_code(self.send(receipt_id='RCPT0003',quantity='0.001'),'OVER_RECEIPT')

    def test_TC11_invalid_json(self):
        self.assert_code(process(self.db,'{"broken":'),'INVALID_JSON')

    def test_TC12_missing_unknown_duplicate_fields(self):
        missing=self.base.copy();missing.pop('quantity')
        for raw in [json.dumps(missing),json.dumps(self.base|{'surprise':1}),
                    json.dumps(self.base)[:-1]+',"quantity":"99"}']:
            self.assert_code(process(self.db,raw),'SCHEMA_ERROR')

    def test_TC13_schema_and_line_types(self):
        for updates in [{'schema_version':2},{'schema_version':True},{'line_number':'1'},
                        {'line_number':True},{'source_system':'wms_demo'},{'receipt_id':'BAD|ID'}]:
            self.assert_code(self.send(**updates),'SCHEMA_ERROR')

    def test_TC14_timestamp_rules(self):
        for stamp in ['2026-02-30T10:00:00Z','2026-10-18T10:00:00','2026-10-18T10:00:00+00:00']:
            self.assert_code(self.send(received_at=stamp),'INVALID_TIMESTAMP')
        self.assert_code(self.send(received_at='2026-10-18T12:05:00.001Z'),'FUTURE_TIMESTAMP')
        self.assert_code(self.send(received_at='2026-09-30T23:59:59Z'),'BEFORE_PO_CREATION')
        self.assertEqual(self.send(received_at='2026-10-18T12:05:00Z')['outcome'],'POSTED')

    def test_TC15_source_and_warehouse(self):
        self.assert_code(self.send(source_system='OTHER'),'UNKNOWN_SOURCE')
        self.assert_code(self.send(warehouse='SECOND'),'UNSUPPORTED_WAREHOUSE')

    def test_TC16_full_reversal_and_retry(self):
        self.send()
        reversal=(ROOT/'examples'/'full_reversal.json').read_text()
        self.assertEqual(process(self.db,reversal)['outcome'],'POSTED')
        self.assertEqual(process(self.db,reversal)['outcome'],'DUPLICATE')
        self.assertEqual(self.scalar('SELECT SUM(delta_milli) FROM receipt'),0)
        self.assertEqual(self.scalar("SELECT on_hand_milli FROM inventory WHERE material_id='MAT100'"),0)

    def test_TC17_unknown_or_wrong_original(self):
        self.assert_code(self.send(action='REVERSAL',original_receipt_id='MISSING'),'ORIGINAL_NOT_FOUND')
        self.send()
        self.assert_code(self.send(receipt_id='REV1',action='REVERSAL',original_receipt_id='RCPT0001',
            po_number='PO1002',uom='KG'),'REVERSAL_REFERENCE_MISMATCH')

    def test_TC18_reversal_quantity_and_order(self):
        self.send()
        self.assert_code(self.send(receipt_id='REV1',action='REVERSAL',original_receipt_id='RCPT0001',quantity='10'),'REVERSAL_QUANTITY')
        self.assert_code(self.send(receipt_id='REV1',action='REVERSAL',original_receipt_id='RCPT0001',
            received_at='2026-10-18T09:00:00Z'),'REVERSAL_TIMESTAMP')

    def test_TC19_double_reversal(self):
        self.send()
        self.send(receipt_id='REV1',action='REVERSAL',original_receipt_id='RCPT0001')
        self.assert_code(self.send(receipt_id='REV2',action='REVERSAL',original_receipt_id='RCPT0001'),'ALREADY_REVERSED')

    def test_TC20_reversal_closed_line_allowed(self):
        self.send()
        with connect(self.db) as conn:
            conn.execute("UPDATE po_line SET status='CLOSED' WHERE po_number='PO1001' AND line_number=1")
        self.assertEqual(self.send(receipt_id='REV1',action='REVERSAL',original_receipt_id='RCPT0001')['outcome'],'POSTED')

    def test_TC21_negative_stock_reversal_guard(self):
        self.send()
        # Boundary fixture represents stock no longer available; downstream consumption is outside demo scope.
        with connect(self.db) as conn:
            conn.execute("UPDATE inventory SET on_hand_milli=5000 WHERE material_id='MAT100'")
        self.assert_code(self.send(receipt_id='REV1',action='REVERSAL',original_receipt_id='RCPT0001'),'NEGATIVE_BALANCE')

    def test_TC22_atomic_rollback_and_retry(self):
        raw=json.dumps(self.base)
        self.assert_code(process(self.db,raw,inject_failure=True),'TECHNICAL_ERROR')
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM receipt'),0)
        self.assertEqual(self.scalar('SELECT SUM(received_milli) FROM po_line'),0)
        self.assertEqual(self.scalar('SELECT SUM(on_hand_milli) FROM inventory'),0)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM attempt WHERE outcome='TECHNICAL_ERROR'"),1)
        self.assertEqual(process(self.db,raw)['outcome'],'POSTED')

    def test_TC23_concurrent_over_receipt_guard(self):
        gate=threading.Barrier(2)
        def worker(identifier):
            gate.wait(timeout=10)
            return self.send(receipt_id=identifier,quantity='60')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(worker,['CONCURRENT1','CONCURRENT2']))
        self.assertEqual(sorted(r['outcome'] for r in results),['POSTED','REJECTED'])
        self.assertEqual(self.scalar('SELECT SUM(delta_milli) FROM receipt'),60000)

    def test_TC24_semantic_retry_canonicalization(self):
        self.send(quantity='25',received_at='2026-10-18T10:00:00Z')
        self.assertEqual(self.send(quantity='25.000',received_at='2026-10-18T10:00:00.000Z')['outcome'],'DUPLICATE')

    def test_TC25_rejected_key_can_be_corrected(self):
        self.assert_code(self.send(quantity='101'),'OVER_RECEIPT')
        self.assertEqual(self.send(quantity='25')['outcome'],'POSTED')

    def test_TC26_fractional_precision(self):
        self.assertEqual(self.send(po_number='PO1002',uom='KG',quantity='0.125')['outcome'],'POSTED')
        self.assertEqual(self.scalar('SELECT SUM(delta_milli) FROM receipt'),125)

    def test_TC27_reversal_field_contract(self):
        self.assert_code(self.send(original_receipt_id='RCPT0001'),'SCHEMA_ERROR')
        self.assert_code(self.send(action='REVERSAL'),'SCHEMA_ERROR')

    def test_TC28_payload_limit(self):
        self.assert_code(process(self.db,' '*16385),'PAYLOAD_TOO_LARGE')


if __name__=='__main__':
    unittest.main()
