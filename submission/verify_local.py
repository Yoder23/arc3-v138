"""Verify a frozen source delivery, then optionally evaluate local public games.

No downloads, uploads, hosted calls, recorded responses or answer files.
The external official game bundle remains outside the delivery.
"""
from pathlib import Path,PurePosixPath
import argparse,ast,hashlib,importlib,json,logging,os,sys,zipfile

def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--output',type=Path,required=True,help='New local directory; existing paths are refused.')
    parser.add_argument('--policy-python',required=True,help='Python interpreter with numpy and scipy.')
    parser.add_argument('--sdk-path',type=Path,help='Optional existing arc-agi SDK source/import directory.')
    parser.add_argument('--environments',type=Path,help='Existing official public game bundle, kept outside delivery.')
    parser.add_argument('--check-only',action='store_true',help='Verify source hashes and initialize the policy; execute zero game actions.')
    args=parser.parse_args();delivery=args.delivery.resolve();output=args.output.resolve()
    if output.exists():raise FileExistsError('Use a new output directory: '+str(output))
    if output==delivery or delivery.is_relative_to(output):raise ValueError('Output must not contain the frozen delivery.')
    ready=read(delivery/'READINESS.json');checks=read(delivery/'CHECKSUMS.json')
    for name,spec in checks.items():
        if Path(name).name!=name:raise ValueError('Invalid delivery member: '+name)
        data=(delivery/name).read_bytes()
        assert sha(data)==spec['sha256']and len(data)==spec['bytes'],name
    payload=(delivery/'policy-package.zip').read_bytes()
    assert sha(payload)==ready['payload_sha256']
    assert sha((delivery/'submission.ipynb').read_bytes())==ready['notebook_sha256']
    with zipfile.ZipFile(delivery/'policy-package.zip')as archive:
        manifest=json.loads(archive.read('MANIFEST.json'))
        expected=set(manifest['files'])|{'MANIFEST.json','requirements.txt'}
        assert set(archive.namelist())==expected and len(archive.namelist())==len(expected)
        for name in archive.namelist():
            path=PurePosixPath(name)
            if path.is_absolute()or '..'in path.parts or '\\'in name or ':'in name:raise ValueError('Unsafe member: '+name)
            data=archive.read(name)
            if name in manifest['files']:
                assert sha(data)==manifest['files'][name]['sha256'],name
                assert name.endswith('.py'),name
                ast.parse(data.decode('utf-8-sig'),filename=name)
        output.mkdir(parents=True);root=output/'source';root.mkdir();archive.extractall(root)
    sys.path.insert(0,str(root));client=importlib.import_module('client')
    with client.PolicyProcess(python=args.policy_python):pass
    report=dict(source_hashes_verified=True,policy_initialized=True,payload_sha256=ready['payload_sha256'],
                notebook_sha256=ready['notebook_sha256'],check_only=args.check_only,new_environment_actions=0,
                kaggle_verified=False,uploaded=False,scope='Local source verification; no hidden evaluation claim.')
    if not args.check_only:
        if args.environments is None or not args.environments.is_dir():raise ValueError('--environments must name an existing local official bundle.')
        if args.sdk_path:
            if not args.sdk_path.is_dir():raise ValueError('--sdk-path must exist locally.')
            sys.path.insert(0,str(args.sdk_path.resolve()))
        from arc_agi import Arcade,OperationMode
        logger=logging.getLogger('local_source_verification');logger.setLevel(logging.ERROR)
        api=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(args.environments.resolve()),recordings_dir=str(output/'records'),logger=logger)
        class Adapter:
            def get_environments(self):return api.get_environments()
            def create_scorecard(self):return api.create_scorecard()
            def make(self,game,**kwargs):
                previous=os.environ.get('ONLY_RESET_LEVELS');os.environ['ONLY_RESET_LEVELS']='false'
                try:return api.make(game,**kwargs)
                finally:
                    if previous is None:os.environ.pop('ONLY_RESET_LEVELS',None)
                    else:os.environ['ONLY_RESET_LEVELS']=previous
                    os.environ['ONLY_RESET_LEVELS']='true'
            def close_scorecard(self,card):return api.close_scorecard(card)
        result=client.play(Adapter(),output/'run',python=args.policy_python)
        report.update(new_environment_actions=result['actions'],result=result,
                      matches_recorded_public_measurement=not result['errors']and result['games']==ready['games']and result['levels']==ready['levels']and result['wins']==ready['wins']and result['actions']==ready['actual_environment_actions']and result['cached_responses']==0 and abs(result['scorer']['score']-ready['local_score'])<1e-9)
        report['scope']='Fresh local evaluation through the official offline interface; no reference response traces are loaded.'
    (output/'VERIFICATION.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items()if k!='result'}))
    if not args.check_only:assert report['matches_recorded_public_measurement'],'Local reproduction differs; inspect the retained local output. Do not replace the frozen package.'

if __name__=='__main__':main()
