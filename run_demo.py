"""Fresh demonstration, regression tests, reconciliation and evidence reports."""
from pathlib import Path
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from interface import AS_OF,canonical_hash,connect,initialize,normalize,process


def main():
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    with (reports/'test_results.txt').open('w',encoding='utf-8') as log:
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit('Tests failed. Inspect reports/test_results.txt.')
    # Isolated fresh DB on every run; does not reset the CLI user's local DB.
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'demo.db';initialize(path)
        valid=(ROOT/'examples'/'valid_receipt.json').read_text()
        reversal=(ROOT/'examples'/'full_reversal.json').read_text()
        conflict=json.dumps(json.loads(valid)|{'quantity':'30'})
        steps=[('First partial receipt',valid),('Identical retry',valid),('Conflicting retry',conflict),
               ('Full reversal',reversal),('Reversal retry',reversal)]
        evidence=[{'step':name,'response':process(path,payload)} for name,payload in steps]
        with connect(path) as db:
            ledger=[dict(row) for row in db.execute('SELECT * FROM receipt ORDER BY receipt_id')]
            balances=[dict(row) for row in db.execute('SELECT * FROM po_line ORDER BY po_number,line_number')]
            inventory=[dict(row) for row in db.execute('SELECT * FROM inventory ORDER BY material_id')]
            attempts=[dict(row) for row in db.execute('SELECT attempt_id,outcome,error_code,http_status,processing_reference FROM attempt ORDER BY attempt_id')]
            assert len(ledger)==2 and sum(row['delta_milli'] for row in ledger)==0
            assert all(row['received_milli']==0 for row in balances)
            assert all(row['on_hand_milli']==0 for row in inventory)
            assert len(attempts)==5
        report={'fixed_demo_clock_utc':AS_OF.isoformat(),'steps':evidence,'receipt_ledger':ledger,
                'po_lines':balances,'inventory':inventory,'attempt_audit':attempts,
                'reconciliation_passed':True}
        (reports/'demo_evidence.json').write_text(json.dumps(report,indent=2)+'\n')
        cli_outcomes=[]
        for name in ['valid_receipt.json','valid_receipt.json','full_reversal.json']:
            run=subprocess.run([sys.executable,str(ROOT/'src'/'cli.py'),str(ROOT/'examples'/name),
                                '--db',str(Path(temp)/'cli.db')],check=True,capture_output=True,text=True)
            cli_outcomes.append(json.loads(run.stdout)['outcome'])
        assert cli_outcomes==['POSTED','DUPLICATE','POSTED']
    fingerprint=canonical_hash(normalize(valid,AS_OF))
    validation={'reference_engine':'Python standard library / SQLite','tests_run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'reference_tests_passed':True,
        'reconciliation_passed':True,'sql_server_execution':'NOT EXECUTED: no SQL Server runtime available',
        'uat_status':'Prepared; business execution and sign-off not performed',
        'live_api_status':'Proposed contract; no HTTP endpoint deployed',
        'canonical_valid_payload_sha256':fingerprint,'cli_sequence':cli_outcomes,
        'verified_source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT/'src'/'interface.py',ROOT/'src'/'cli.py',ROOT/'tests'/'test_interface.py',ROOT/'run_demo.py']}}
    (reports/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(json.dumps(validation,indent=2))


if __name__=='__main__':
    main()
