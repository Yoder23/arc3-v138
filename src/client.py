"""Sequential legal-observation driver; no benchmark responses or game policy IDs."""
from pathlib import Path
from collections import deque
import hashlib,json,os,queue,subprocess,sys,threading,time
ROOT=Path(__file__).resolve().parent
class PolicyProcess:
 def __init__(self,python=None):
  self.q=queue.Queue();self.closed=False;self.errors=deque(maxlen=20)
  self.p=subprocess.Popen([python or sys.executable,'-B',str(ROOT/'policy/student.py'),'--arm','selective'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT,env={**os.environ,'PYTHONHASHSEED':'0','PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','CUDA_VISIBLE_DEVICES':''},creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt'else 0)
  def read():
   for line in self.p.stdout:self.q.put(line)
   self.q.put(None)
  def errors():
   for line in self.p.stderr:self.errors.append(line[-1500:])
  threading.Thread(target=read,daemon=True).start();threading.Thread(target=errors,daemon=True).start()
  try:
   line=self.q.get(timeout=90)
   if line is None:raise RuntimeError('Policy initialization failed: '+''.join(self.errors)[-1500:])
   if json.loads(line)!={'ready':True,'arm':'selective'}:raise RuntimeError('Invalid policy handshake')
  except BaseException:
   self.close();raise
 def respond(self,o,timeout=120):
  assert set(o)=={'frame','animation_frames','state','available_actions','levels_completed'}
  self.p.stdin.write(json.dumps(o,separators=(',',':'))+'\n');self.p.stdin.flush();line=self.q.get(timeout=timeout)
  if line is None:raise RuntimeError('Policy stopped: '+''.join(self.errors)[-1500:])
  return json.loads(line)
 def close(self):
  if not self.closed:
   self.closed=True
   if self.p.poll()is None:self.p.kill()
   self.p.wait(timeout=10)
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
def legal(obs,env):
 if obs is None:raise RuntimeError('Missing environment observation')
 f=obs.frame[-1];return dict(frame=f.tolist()if hasattr(f,'tolist')else f,animation_frames=[v.tolist()if hasattr(v,'tolist')else v for v in obs.frame],state=obs.state.value,available_actions=[a.value for a in env.action_space],levels_completed=obs.levels_completed)
def play(arc,output,python=None,actions=1024,game_seconds=600,whole_seconds=28800,on_event=None,on_finish=None):
 from arcengine import GameAction
 output=Path(output);output.mkdir(parents=True,exist_ok=False);start=time.monotonic();games=sorted(arc.get_environments(),key=lambda g:g.game_id);card=arc.create_scorecard();rows=[]
 try:
  for index,game in enumerate(games):
   remaining=whole_seconds-(time.monotonic()-start);budget=min(game_seconds,max(0,(remaining-120)/(len(games)-index)))
   row=dict(game_id=game.game_id,actions=0,levels=0,status='not_started');rows.append(row)
   if budget<=0:row['status']='whole_run_budget';continue
   began=time.monotonic();worker=None;response=None;o=None
   try:
    env=arc.make(game.game_id,seed=0,scorecard_id=card,save_recording=False)
    if env is None:raise RuntimeError('Environment initialization failed')
    worker=PolicyProcess(python);o=legal(env.observation_space,env);row['status']='action_limit'
    for t in range(actions):
     if o['state']=='WIN':row['status']='win';break
     remain=budget-(time.monotonic()-began)
     if remain<=0:row['status']='time_limit';break
     response=worker.respond(o,timeout=min(120,remain))
     if response['done']:row['status']='student_stopped';break
     a=response['action'];data=response.get('data',{})
     if type(a)is not int or not(a==0 or a in o['available_actions']):raise ValueError('Illegal policy action')
     if a==6 and(set(data)!={'x','y'}or any(type(v)is not int or not 0<=v<64 for v in data.values())):raise ValueError('Illegal coordinates')
     after=legal(env.reset()if a==0 else env.step(GameAction.from_id(a),data=data),env)
     row.update(actions=t+1,levels=after['levels_completed'])
     if on_event:on_event(game.game_id,t,o,response,after)
     o=after;row.update(actions=t+1,levels=o['levels_completed'])
     if o['state']=='WIN':row['status']='win';break
    if on_finish:on_finish(game.game_id,row,o,response)
   except Exception as e:row.update(status='error',error=type(e).__name__+': '+str(e)[:500])
   finally:
    if worker:worker.close()
    row['seconds']=round(time.monotonic()-began,3);(output/'PROGRESS.json').write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
 finally:
  (output/'SEALED.json').write_text(json.dumps({'rows_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),'games':len(rows)}))
  score=arc.close_scorecard(card)
 result=dict(games=len(games),rows=rows,actions=sum(r['actions']for r in rows),levels=sum(r['levels']for r in rows),wins=sum(r['status']=='win'for r in rows),errors=[r['game_id']for r in rows if r['status']in('error','time_limit','whole_run_budget','not_started')],seconds=round(time.monotonic()-start,3),cached_responses=0,hosted_compliance=False)
 if score is not None:
  result['scorer']={k:getattr(score,k,None)for k in('score','total_environments','total_levels','total_levels_completed','total_actions')}
 (output/'RESULT.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 from arc_agi import Arcade,OperationMode
 os.environ['ARC_BASE_URL']='http://gateway:8001/';os.environ['ARC_API_KEY']='test-key-123';os.environ['ENVIRONMENTS_DIR']='';os.environ['RECORDINGS_DIR']='/tmp/arc3-recordings'
 arcade=Arcade(operation_mode=OperationMode.COMPETITION);result=play(arcade,'/tmp/arc3-candidate-run');print(json.dumps({k:v for k,v in result.items()if k!='rows'}))
 if result['errors']:raise SystemExit('Candidate runtime errors: '+str(result['errors']))
