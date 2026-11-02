"""Bounded legal-view discovery of conditional controls and state-action coverage."""
from collections import Counter,deque
import copy,hashlib,json
import numpy as np
from scipy import ndimage

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def parts(frame):
    f=np.asarray(frame);out=[]
    for color in sorted(set(f.ravel())):
        lab,_=ndimage.label(f==color)
        for i,b in enumerate(ndimage.find_objects(lab)):
            if b is None:continue
            ys,xs=np.where(lab[b]==i+1);n=len(ys);y,x=b[0].start,b[1].start;h,w=b[0].stop-y,b[1].stop-x
            if y==0 or x==0 or y+h>=64 or x+w>=64:continue
            out.append(dict(color=int(color),area=n,y=y,x=x,h=h,w=w,shape=tuple(zip(ys.tolist(),xs.tolist()))))
    return out
def state(obs):return digest([obs['levels_completed'],obs['frame'][:62]])
class Learner:
    def __init__(self):
        self.previous=None;self.last=None;self.edges={};self.outcomes=[];self.control_sites=None;self.submit=None;self.bits=[];self.target_bits=[];self.trial=0;self.phase='configure';self.moves={};self.mover=None;self.steps=0
    def detect(self,obs):
        ps=parts(obs['frame']);rows={}
        for q in ps:
            if q['h']==1 and q['w']==3 and q['area']==3 and any(r['color']==q['color'] and r['h']==3 and r['w']==1 and r['y']==q['y']+2 and r['x']==q['x']+1 for r in ps):rows.setdefault(q['y'],[]).append(q)
        rows=[sorted(v,key=lambda q:q['x']) for v in rows.values() if 3<=len(v)<=8]
        if len(rows)!=1:return False
        bars=rows[0];buttons=[q for q in ps if 5<=q['h']<=16 and 5<=q['w']<=16 and q['area']>=20 and q['y']>=bars[0]['y']+5]
        if len(buttons)!=1:return False
        self.control_sites=[dict(x=q['x']+1,y=q['y']+2) for q in bars];q=buttons[0];self.submit=dict(x=q['x']+q['w']//2,y=q['y']+q['h']//2);self.bits=[0]*len(bars);self.target_bits=self.bits[:];return True
    def observe(self,obs):
        if self.previous is None:return
        old=self.previous;action,data=self.last;src=state(old);dst=state(obs);self.edges.setdefault(src,{})[(action,tuple(sorted(data.items())))]=dst
        a=np.array(old['frame']);b=np.array(obs['frame']);changed=int((a[7:62]!=b[7:62]).sum());row=dict(source=digest(dict(before=old,action=action,data=data,after=obs)),action=action,data=data,changed_pixels=changed,progress=obs['levels_completed']>old['levels_completed'] or obs['state']=='WIN',configuration=list(self.bits),phase=self.phase)
        self.outcomes.append(row)
        if action!=6:
            left=parts(old['frame']);right=parts(obs['frame']);candidates=[]
            for q in left:
                if not(3<=q['h']<=12 and 3<=q['w']<=12 and 8<=q['area']<=150):continue
                matches=[r for r in right if r['shape']==q['shape'] and r['color']==q['color']]
                if len(matches)!=1:continue
                r=matches[0];dy,dx=r['y']-q['y'],r['x']-q['x']
                if 0<abs(dy)+abs(dx)<=12:candidates.append((q,r,dy,dx))
            if len(candidates)==1:
                q,r,dy,dx=candidates[0];self.moves[action]=(dy,dx);self.mover=r
        if obs['levels_completed']!=old['levels_completed'] or obs['state']=='GAME_OVER':self.control_sites=None;self.bits=[];self.phase='configure'
    def choose(self,obs):
        if obs['state']=='WIN':return None,{}
        if obs['state'] in ('GAME_OVER','NOT_PLAYED'):return 0,{}
        if obs['available_actions']==[6] and (self.control_sites is not None or self.detect(obs)):
            n=len(self.bits);gray=(self.trial%(1<<n))^((self.trial%(1<<n))>>1);self.target_bits=[(gray>>i)&1 for i in range(n)]
            different=[i for i in range(n) if self.bits[i]!=self.target_bits[i]]
            if different:
                i=different[0];self.bits[i]^=1;self.phase='configure';return 6,self.control_sites[i]
            self.phase='execute';self.trial+=1;return 6,self.submit
        s=state(obs);legal=[(a,()) for a in sorted(obs['available_actions']) if a!=6];known=self.edges.get(s,{})
        unseen=[q for q in legal if q not in known]
        def rank(q):
            action=q[0];delta=self.moves.get(action);targets=[]
            if self.mover and delta:
                for p in parts(obs['frame']):
                    if p['color']==self.mover['color'] and 5<=p['area']<=150 and p['shape']!=self.mover['shape'] and p['y']>=7:
                        targets.append(abs(self.mover['y']+delta[0]-p['y'])+abs(self.mover['x']+delta[1]-p['x']))
            return (min(targets) if targets else 100,action)
        if unseen:return min(unseen,key=rank)[0],{}
        queue=deque([(s,[])]);seen={s}
        while queue and len(seen)<2048:
            here,path=queue.popleft()
            if path and any(q not in self.edges.get(here,{}) for q in legal):return path[0][0],dict(path[0][1])
            for action,dest in sorted(self.edges.get(here,{}).items()):
                if dest not in seen:seen.add(dest);queue.append((dest,path+[action]))
        return (legal[self.steps%len(legal)][0],{}) if legal else (6,dict(x=32,y=32))
    def respond(self,obs):
        self.observe(obs);a,d=self.choose(obs);self.previous=copy.deepcopy(obs);self.last=(a,d);self.steps+=1
        return dict(action=a,data=d,done=a is None,certificate=None,advisor='conditional_control_discovery',diagnostics=dict(retained_transitions=len(self.outcomes),distinct_states=len(self.edges),control_sites=self.control_sites,submit=self.submit,trial=self.trial,moves=self.moves,last_outcome=self.outcomes[-1] if self.outcomes else None))
