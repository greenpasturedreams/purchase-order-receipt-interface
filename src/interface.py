"""Executable reference behavior. SQLite demo; not a SQL Server runtime or HTTP service."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
import hashlib
import json
import re
import sqlite3

AS_OF = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
FIELDS = {'schema_version','source_system','receipt_id','action','po_number','line_number',
          'quantity','uom','warehouse','received_at','original_receipt_id'}
REQUIRED = FIELDS-{'original_receipt_id'}
ID = re.compile(r'^[A-Z0-9_-]{1,40}$')
QTY = re.compile(r'^[0-9]{1,15}(?:\.[0-9]{1,3})?$')
STAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$')


class Rejection(Exception):
    def __init__(self, code, message, status=422):
        self.code, self.message, self.status = code, message, status


@contextmanager
def connect(path):
    db = sqlite3.connect(path, timeout=15, isolation_level=None)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
    finally:
        db.close()


def initialize(path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with connect(path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS po_line (
          po_number TEXT NOT NULL,line_number INTEGER NOT NULL,material_id TEXT NOT NULL,
          uom TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('OPEN','CLOSED')),
          created_at TEXT NOT NULL,ordered_milli INTEGER NOT NULL,
          received_milli INTEGER NOT NULL DEFAULT 0 CHECK(received_milli>=0),
          PRIMARY KEY(po_number,line_number),CHECK(received_milli<=ordered_milli));
        CREATE TABLE IF NOT EXISTS inventory (
          warehouse TEXT NOT NULL,material_id TEXT NOT NULL,
          on_hand_milli INTEGER NOT NULL CHECK(on_hand_milli>=0),PRIMARY KEY(warehouse,material_id));
        CREATE TABLE IF NOT EXISTS receipt (
          source_system TEXT NOT NULL,receipt_id TEXT NOT NULL,action TEXT NOT NULL,
          po_number TEXT NOT NULL,line_number INTEGER NOT NULL,quantity_milli INTEGER NOT NULL,
          delta_milli INTEGER NOT NULL,uom TEXT NOT NULL,warehouse TEXT NOT NULL,
          received_at TEXT NOT NULL,original_receipt_id TEXT,payload_hash TEXT NOT NULL,
          PRIMARY KEY(source_system,receipt_id),
          FOREIGN KEY(po_number,line_number) REFERENCES po_line(po_number,line_number));
        CREATE UNIQUE INDEX IF NOT EXISTS one_full_reversal
          ON receipt(source_system,original_receipt_id) WHERE action='REVERSAL';
        CREATE TABLE IF NOT EXISTS attempt (
          attempt_id INTEGER PRIMARY KEY,source_system TEXT,receipt_id TEXT,
          received_request_at TEXT NOT NULL,payload_json TEXT NOT NULL,input_sha256 TEXT NOT NULL,
          outcome TEXT NOT NULL,error_code TEXT,http_status INTEGER NOT NULL,
          processing_reference TEXT);
        ''')
        db.executemany('INSERT OR IGNORE INTO po_line VALUES (?,?,?,?,?,?,?,?)',[
          ('PO1001',1,'MAT100','EA','OPEN','2026-10-01T00:00:00.000Z',100000,0),
          ('PO1001',2,'MAT200','EA','CLOSED','2026-10-01T00:00:00.000Z',50000,0),
          ('PO1002',1,'MAT300','KG','OPEN','2026-10-01T00:00:00.000Z',200000,0)])
        db.executemany('INSERT OR IGNORE INTO inventory VALUES (?,?,?)',
                       [('MAIN',m,0) for m in ['MAT100','MAT200','MAT300']])


def normalize(raw, as_of):
    if len(raw.encode('utf-8'))>16384:
        raise Rejection('PAYLOAD_TOO_LARGE','Payload exceeds 16 KiB.',413)
    def unique_pairs(pairs):
        values={}
        for key,value in pairs:
            if key in values:
                raise Rejection('SCHEMA_ERROR','Duplicate JSON property.',400)
            values[key]=value
        return values
    try:
        p=json.loads(raw,object_pairs_hook=unique_pairs)
    except (json.JSONDecodeError,UnicodeError):
        raise Rejection('INVALID_JSON','Request must be valid JSON.',400)
    if not isinstance(p,dict) or not REQUIRED.issubset(p) or set(p)-FIELDS:
        raise Rejection('SCHEMA_ERROR','Missing required or unsupported fields.',400)
    if type(p['schema_version']) is not int or p['schema_version']!=1:
        raise Rejection('SCHEMA_ERROR','schema_version must be integer 1.',400)
    for field in ['source_system','receipt_id','po_number','uom','warehouse']:
        if not isinstance(p[field],str) or not ID.fullmatch(p[field]):
            raise Rejection('SCHEMA_ERROR',f'Invalid {field}.',400)
    if type(p['line_number']) is not int or not 1<=p['line_number']<=2147483647:
        raise Rejection('SCHEMA_ERROR','line_number must be a positive 32-bit integer.',400)
    if p['action'] not in ['RECEIPT','REVERSAL']:
        raise Rejection('SCHEMA_ERROR','Invalid action.',400)
    if not isinstance(p['quantity'],str) or not QTY.fullmatch(p['quantity']) or Decimal(p['quantity'])<=0:
        raise Rejection('INVALID_QUANTITY','quantity must be a positive decimal string with at most 3 decimal places.')
    p['quantity']=f"{Decimal(p['quantity']):.3f}"
    if not isinstance(p['received_at'],str) or not STAMP.fullmatch(p['received_at']):
        raise Rejection('INVALID_TIMESTAMP','Use an ISO UTC timestamp ending in Z.',400)
    try:
        ts=datetime.fromisoformat(p['received_at'].replace('Z','+00:00'))
    except ValueError:
        raise Rejection('INVALID_TIMESTAMP','Timestamp is not a real date/time.',400)
    if ts>as_of+timedelta(minutes=5):
        raise Rejection('FUTURE_TIMESTAMP','Timestamp is more than 5 minutes in the future.')
    p['received_at']=ts.isoformat(timespec='milliseconds').replace('+00:00','Z')
    original=p.get('original_receipt_id')
    if p['action']=='RECEIPT' and original is not None:
        raise Rejection('SCHEMA_ERROR','Receipts must not reference an original receipt.',400)
    if p['action']=='REVERSAL' and (not isinstance(original,str) or not ID.fullmatch(original)):
        raise Rejection('SCHEMA_ERROR','Reversal requires original_receipt_id.',400)
    p['original_receipt_id']=original
    return p


def canonical_hash(p):
    fields=['schema_version','source_system','receipt_id','action','po_number','line_number',
            'quantity','uom','warehouse','received_at','original_receipt_id']
    canonical='|'.join('' if p[k] is None else str(p[k]) for k in fields)
    return hashlib.sha256(canonical.encode('ascii')).hexdigest()


def process(path,raw,as_of=AS_OF,inject_failure=False):
    """One request → one audited response. Transactions protect all business writes."""
    p=None
    with connect(path) as db:
        try:
            p=normalize(raw,as_of)
            if p['source_system']!='WMS_DEMO':
                raise Rejection('UNKNOWN_SOURCE','Source is not registered.')
            if p['warehouse']!='MAIN':
                raise Rejection('UNSUPPORTED_WAREHOUSE','Version 1 supports MAIN only.')
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT * FROM receipt WHERE source_system=? AND receipt_id=?',
                (p['source_system'],p['receipt_id'])).fetchone()
            fingerprint=canonical_hash(p)
            if prior is not None:
                if prior['payload_hash']!=fingerprint:
                    raise Rejection('IDEMPOTENCY_CONFLICT','Posted key has a different business payload.',409)
                outcome,status='DUPLICATE',200
            else:
                line=db.execute('SELECT * FROM po_line WHERE po_number=? AND line_number=?',
                                (p['po_number'],p['line_number'])).fetchone()
                if line is None:
                    raise Rejection('UNKNOWN_PO_LINE','Purchase-order line does not exist.')
                if p['uom']!=line['uom']:
                    raise Rejection('UOM_MISMATCH','Unit does not match purchase-order line.')
                if p['received_at']<line['created_at']:
                    raise Rejection('BEFORE_PO_CREATION','Timestamp precedes PO creation.')
                qty=int(Decimal(p['quantity'])*1000)
                if p['action']=='RECEIPT':
                    if line['status']!='OPEN':
                        raise Rejection('PO_LINE_CLOSED','New receipts require an open line.')
                    if line['received_milli']+qty>line['ordered_milli']:
                        raise Rejection('OVER_RECEIPT','Receipt exceeds remaining ordered quantity.')
                    delta=qty
                else:
                    original=db.execute('SELECT * FROM receipt WHERE source_system=? AND receipt_id=?',
                        (p['source_system'],p['original_receipt_id'])).fetchone()
                    if original is None or original['action']!='RECEIPT':
                        raise Rejection('ORIGINAL_NOT_FOUND','Original posted receipt was not found.')
                    if (original['po_number'],original['line_number'],original['warehouse'],original['uom'])!=(p['po_number'],p['line_number'],p['warehouse'],p['uom']):
                        raise Rejection('REVERSAL_REFERENCE_MISMATCH','Original receipt belongs to different business dimensions.')
                    if db.execute("SELECT 1 FROM receipt WHERE source_system=? AND original_receipt_id=? AND action='REVERSAL'",
                        (p['source_system'],p['original_receipt_id'])).fetchone():
                        raise Rejection('ALREADY_REVERSED','Original receipt already has a full reversal.',409)
                    if qty!=original['quantity_milli']:
                        raise Rejection('REVERSAL_QUANTITY','Version 1 requires full original quantity.')
                    if p['received_at']<original['received_at']:
                        raise Rejection('REVERSAL_TIMESTAMP','Reversal cannot predate original receipt.')
                    delta=-qty
                inventory=db.execute('SELECT on_hand_milli FROM inventory WHERE warehouse=? AND material_id=?',
                    (p['warehouse'],line['material_id'])).fetchone()
                if inventory is None:
                    raise Rejection('INVENTORY_NOT_CONFIGURED','Material is not configured at warehouse.')
                if inventory[0]+delta<0 or line['received_milli']+delta<0:
                    raise Rejection('NEGATIVE_BALANCE','Reversal would create a negative balance.')
                db.execute('INSERT INTO receipt VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (p['source_system'],p['receipt_id'],p['action'],p['po_number'],p['line_number'],qty,
                     delta,p['uom'],p['warehouse'],p['received_at'],p['original_receipt_id'],fingerprint))
                if inject_failure:
                    raise RuntimeError('Injected failure after ledger insert')
                db.execute('UPDATE po_line SET received_milli=received_milli+? WHERE po_number=? AND line_number=?',
                           (delta,p['po_number'],p['line_number']))
                db.execute('UPDATE inventory SET on_hand_milli=on_hand_milli+? WHERE warehouse=? AND material_id=?',
                           (delta,p['warehouse'],line['material_id']))
                outcome,status='POSTED',201
            reference=f"{p['source_system']}/{p['receipt_id']}"
            response={'outcome':outcome,'http_status':status,'processing_reference':reference,'error_code':None}
            # Success audit is in the same transaction as ledger and balances.
            record_attempt(db,p,raw,as_of,response)
            db.execute('COMMIT')
            return response
        except Rejection as error:
            if db.in_transaction:
                db.execute('ROLLBACK')
            response={'outcome':'REJECTED','http_status':error.status,'processing_reference':None,
                      'error_code':error.code,'message':error.message}
        except Exception:
            if db.in_transaction:
                db.execute('ROLLBACK')
            response={'outcome':'TECHNICAL_ERROR','http_status':503,'processing_reference':None,
                      'error_code':'TECHNICAL_ERROR','message':'Processing rolled back. Retry the identical request.'}
        record_attempt(db,p,raw,as_of,response)
        return response


def record_attempt(db,p,raw,as_of,response):
    db.execute('''INSERT INTO attempt(source_system,receipt_id,received_request_at,payload_json,input_sha256,
       outcome,error_code,http_status,processing_reference) VALUES (?,?,?,?,?,?,?,?,?)''',
       ((p or {}).get('source_system'),(p or {}).get('receipt_id'),as_of.isoformat(),raw[:16384],
        hashlib.sha256(raw.encode('utf-8')).hexdigest(),response['outcome'],response['error_code'],
        response['http_status'],response['processing_reference']))
