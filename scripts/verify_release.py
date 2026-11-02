"""Offline integrity verification of the frozen public V138 release."""
from pathlib import Path
import ast, base64, hashlib, io, json, lzma, zipfile

ROOT = Path(__file__).resolve().parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
    record = json.loads((ROOT/'RELEASE-MANIFEST.json').read_text(encoding='utf-8'))
    for name, item in record['files'].items():
        p = (ROOT/name).resolve()
        assert p.is_relative_to(ROOT), name
        b = p.read_bytes()
        assert len(b)==item['bytes'] and sha(b)==item['sha256'], name
    npath = ROOT/'submission/submission.ipynb'
    n = json.loads(npath.read_text(encoding='utf-8'))
    assert npath.stat().st_size < 1000000
    for cell in n['cells']:
        if cell['cell_type']=='code': compile(cell['source'], '<notebook>', 'exec')
    tree = ast.parse(n['cells'][1]['source'])
    encoded = ast.literal_eval(tree.body[1].value.args[0].args[0])
    payload = lzma.decompress(base64.b85decode(encoded))
    assert payload == (ROOT/'submission/policy-package.zip').read_bytes()
    info = json.loads((ROOT/'release-info.json').read_text())
    assert sha(payload)==info['policy_zip_sha256'] and sha(npath.read_bytes())==info['notebook_sha256']
    count = 0
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        manifest = json.loads(z.read('MANIFEST.json'))
        assert set(z.namelist()) == set(manifest['files'])|{'MANIFEST.json','requirements.txt'}
        assert len(z.namelist()) == len(set(z.namelist()))
        source_names = {p.relative_to(ROOT/'src').as_posix() for p in (ROOT/'src').rglob('*') if p.is_file()}
        assert source_names == set(z.namelist())
        for name in z.namelist():
            b = z.read(name)
            assert b == (ROOT/'src'/name).read_bytes(), name
            if name in manifest['files']:
                assert sha(b)==manifest['files'][name]['sha256']
                compile(b.decode('utf-8-sig'), name, 'exec')
                count += 1
    assert count == 558
    print(json.dumps({'passed':True,'files_verified':len(record['files']),'python_sources':count,'notebook_bytes':npath.stat().st_size,'policy_zip_sha256':sha(payload),'game_actions':0}))
if __name__=='__main__': main()
