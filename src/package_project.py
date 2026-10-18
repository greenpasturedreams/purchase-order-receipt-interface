"""Check local links, traceability coverage and fresh test evidence; create upload ZIP."""
from pathlib import Path
import ast
import hashlib
import json
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    validation=json.loads((ROOT/'reports'/'validation.json').read_text(encoding='utf-8'))
    assert validation['reference_tests_passed'] and validation['reconciliation_passed']
    assert validation['tests_run']==28 and validation['failures']==validation['errors']==0
    assert validation['cli_sequence']==['POSTED','DUPLICATE','POSTED']
    for name,digest in validation['verified_source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,f'Stale test evidence: {name}'
    tree=ast.parse((ROOT/'tests'/'test_interface.py').read_text(encoding='utf-8'))
    tested={re.search(r'TC\d{2}',node.name).group() for node in ast.walk(tree)
            if isinstance(node,ast.FunctionDef) and node.name.startswith('test_TC')}
    plan=(ROOT/'docs'/'05_TEST_PLAN_AND_UAT.md').read_text(encoding='utf-8')
    assert all(test in plan for test in tested)
    matrix=(ROOT/'docs'/'04_REQUIREMENTS_AND_TRACEABILITY.md').read_text(encoding='utf-8')
    assert all(f'FR{i:02}' in matrix for i in range(1,12))
    link_count=0
    for path in ROOT.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if target.startswith(('https:','http:','#')):
                continue
            assert (path.parent/target.split('#')[0]).exists(),f'Broken link: {path}: {target}'
            link_count+=1
    report={'local_markdown_links_checked':link_count,'automated_test_ids_in_plan':len(tested),
            'functional_requirement_ids':11,'fresh_reference_evidence_verified':True,
            'sql_server_runtime_validation':'Pending; not inferred from reference tests'}
    (ROOT/'reports'/'package_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    files=[p for p in ROOT.rglob('*') if p.is_file() and 'runtime' not in p.relative_to(ROOT).parts
           and '__pycache__' not in p.parts and '.venv' not in p.parts and p.suffix!='.pyc']
    assert all(p.stat().st_size<25*1024*1024 for p in files)
    archive=ROOT.parent/'purchase_order_receipt_interface.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as out:
        for path in sorted(files):
            out.write(path,path.relative_to(ROOT))
    with zipfile.ZipFile(archive) as out:
        assert out.testzip() is None and 'README.md' in out.namelist()
        assert not any(name.endswith('.db') for name in out.namelist())
    print(json.dumps(report,indent=2))
    print(f'Created {archive.name}: {len(files)} files, {archive.stat().st_size:,} bytes')


if __name__=='__main__':
    main()
