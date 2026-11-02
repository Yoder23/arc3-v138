"""Rebuild the frozen ZIP from readable source and reproduce the compact notebook."""
from pathlib import Path
import argparse, base64, copy, hashlib, io, json, lzma, zipfile

ROOT = Path(__file__).resolve().parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    if args.output.exists(): raise FileExistsError('Use a new output directory.')
    info=json.loads((ROOT/'release-info.json').read_text())
    original=(ROOT/'submission/policy-package.zip').read_bytes()
    assert sha(original)==info['policy_zip_sha256']
    buffer=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as template, zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as dest:
        dest.comment=template.comment
        for item in template.infolist():
            dest.writestr(copy.copy(item),(ROOT/'src'/item.filename).read_bytes())
    payload=buffer.getvalue()
    assert payload==original, 'Rebuilt ZIP differs. Check source bytes and local compression runtime.'
    n=json.loads((ROOT/'submission/submission.ipynb').read_text(encoding='utf-8'))
    lines=n['cells'][1]['source'].splitlines(keepends=True)
    encoded=base64.b85encode(lzma.compress(payload,preset=9)).decode('ascii')
    lines[1]='payload=lzma.decompress(base64.b85decode('+repr(encoded)+'))\n'
    n['cells'][1]['source']=''.join(lines)
    notebook=(json.dumps(n,indent=2)+'\n').encode('utf-8')
    assert sha(notebook)==info['notebook_sha256'], 'Notebook differs; compression library versions may differ.'
    assert len(notebook)<1000000
    args.output.mkdir(parents=True)
    (args.output/'policy-package.zip').write_bytes(payload)
    (args.output/'submission.ipynb').write_bytes(notebook)
    print(json.dumps({'passed':True,'policy_zip_sha256':sha(payload),'notebook_sha256':sha(notebook),'notebook_bytes':len(notebook)}))
if __name__=='__main__': main()
