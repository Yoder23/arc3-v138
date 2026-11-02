"""Learn click effects on matched moving/reference markers from legal pixels."""
import copy,heapq
from collections import defaultdict,Counter
from binary_demonstration_bootstrap_v1 import components
from observed_compartments_v2 import discover,positions
from marker_compartment_binding_v2 import targets as bound_targets
from compartment_prerequisites_v4 import proposals

def scene(frame):
    groups=defaultdict(list)
    for o in components(frame):groups[o['ink']].append(o)
    pairs=[]
    for ink,obs in groups.items():
        if len(obs)!=2:continue
        if not all(o['box'][0]>0 and len(o['shape'])==o['box'][2]*o['box'][3] and
                   min(o['box'][2:])<=4 and max(o['box'][2:])<=8 and o['box'][2]!=o['box'][3] for o in obs):continue
        a,b=sorted(obs,key=lambda o:len(o['shape']))
        if len(a['shape'])==len(b['shape']):continue
        if (a['box'][2]>a['box'][3])!=(b['box'][2]>b['box'][3]):continue
        axis=1 if b['box'][2]>b['box'][3] else 0
        pairs.append(dict(ink=ink,axis=axis,actor=b,reference=a,current=b['box'][axis],target=a['box'][axis]))
    pairs.sort(key=lambda p:p['ink'])
    candidates=[]
    for ink,obs in groups.items():
        squares=[o for o in obs if o['box'][0]>=0 and 2<=o['box'][2]==o['box'][3]<=5 and len(o['shape'])==o['box'][2]**2]
        if len(squares)>=2:candidates.append((len(squares),-sum(o['box'][2]for o in squares),ink,squares))
    if not pairs or not candidates:return None
    _,_,_,squares=max(candidates)
    extras=[]
    used={p['ink']for p in pairs}|{squares[0]['ink']}
    for ink,obs in groups.items():
        if ink in used or len(obs)<2:continue
        a,b=obs[:2]
        if all(o['box'][2:]==a['box'][2:]for o in obs) and a['box'][2:]==b['box'][2:] and a['box'][2]!=a['box'][3] and 8<=len(a['shape'])<=64 and all(len(o['shape'])==o['box'][2]*o['box'][3]for o in obs):extras+=obs
    squares=sorted(squares,key=lambda o:o['box'])+sorted(extras,key=lambda o:o['box'])
    buttons=[dict(ink=o['ink'],box=o['box'],point=dict(x=o['box'][1]+o['box'][3]//2,y=o['box'][0]+o['box'][2]//2))for o in squares]
    return dict(pairs=pairs,buttons=buttons,positions=tuple(p['current']for p in pairs),targets=tuple(p['target']for p in pairs))

def plan(start,target,models,bounds,limit=24000):
    matches=lambda q:all(t is None or v==t for v,t in zip(q,target))
    if matches(start):return []
    effects=sorted((i,tuple(v))for i,v in models.items()if any(v))
    if not effects:return None
    maxstep=max(sum(abs(v)for v in d)for _,d in effects)
    distance=lambda q:sum(abs(x-y)for x,y in zip(q,target)if y is not None)
    queue=[(distance(start)/maxstep,0,start,[])];costs={start:0};n=0
    while queue and n<limit:
        _,cost,q,path=heapq.heappop(queue);n+=1
        if matches(q):return path
        if cost!=costs[q] or cost>=64:continue
        for i,d in effects:
            dest=tuple(x+y for x,y in zip(q,d))
            if any(not lo<=v<=hi for v,(lo,hi)in zip(dest,bounds)) or cost+1>=costs.get(dest,10**9):continue
            costs[dest]=cost+1;heapq.heappush(queue,(cost+1+distance(dest)/maxstep,cost+1,dest,path+[i]))
    return None

class Agent:
    def __init__(self,prior=None):
        self.prior=prior;self.active=True;self.level=None;self.t=0;self.previous=None
        self.aux=None;self.probe_trials=[];self.control_context=None;self.geometry=None;self.models={};self.evidence=[];self.failures=[];self.archive=[];self.tried=Counter();self.visits=Counter()
    def respond(self,raw):
        if raw['state']!='NOT_FINISHED':return dict(done=True,action=None,data={})
        s=scene(raw['frame'])
        if not s:return dict(done=True,action=None,data={})
        if raw['levels_completed']!=self.level:
            if self.level is not None:self.archive.append(dict(level=self.level,evidence=copy.deepcopy(self.evidence),failures=copy.deepcopy(self.failures),models=copy.deepcopy(self.models)))
            self.level=raw['levels_completed'];self.aux=None;self.probe_trials=[];self.control_context=None;self.geometry=discover(raw['frame'],s);self.buttons=copy.deepcopy(s['buttons']);self.previous=None;self.models={};self.evidence=[];self.failures=[];self.tried=Counter();self.visits=Counter()
        if self.geometry is None:return dict(done=True,action=None,data={})
        s['buttons']=copy.deepcopy(self.buttons)
        s['marker_positions']=s['positions'];s['positions']=positions(raw['frame'],self.geometry);s['targets']=bound_targets(s,self.geometry)
        if self.previous:
            p=self.previous;before=p['scene'];idx=p['index']
            if [x['ink']for x in before['pairs']]==[x['ink']for x in s['pairs']]:
                delta=tuple(b-a for a,b in zip(before['positions'],s['positions']))
                record=dict(source=p['source'],index=idx,data=before['buttons'][idx]['point'],before=before['positions'],after=s['positions'],delta=delta,markers=[x['ink']for x in s['pairs']])
                self.evidence.append(record)
                if idx in self.models and tuple(self.models[idx])!=delta:
                    self.failures.append(dict(source=p['source'],index=idx,expected=self.models[idx],actual=delta,kind='conditional_or_clipped_effect'))
                if any(delta):self.models[idx]=delta
                self.visits[(s['positions'],idx)]+=0
        context=tuple((p['ink'],p['actor']['box'][1-self.geometry['axis']])for p in s['pairs'])
        if context!=self.control_context:self.aux=None;self.control_context=context
        active_trials=[tuple(t['key'])for t in self.probe_trials if t['context']==context]
        target=s['targets'];pos=s['positions'];path=plan(pos,target,self.models,[z['bounds']for z in self.geometry['segments']]);idx=None;tag='inquire_click_effect'
        intervention=None
        if self.aux is not None and all(t is None or v==t for v,t in zip(pos,self.aux['targets'])):
            if self.aux.get('conditional_click'):intervention=next(i for i,b in enumerate(s['buttons'])if b['point']==self.aux['aperture']['point'])
            self.probe_trials.append(dict(context=context,key=tuple(self.aux['key'])));active_trials.append(tuple(self.aux['key']));self.aux=None
        if not path and all(self.tried[i]>0 for i in range(len(s['buttons']))):
            hypotheses=([self.aux]if self.aux else [])+proposals(s,dict(self.geometry,targets=s['targets']),self.models,active_trials)
            for h in hypotheses:
                route=plan(pos,h['targets'],self.models,[z['bounds']for z in self.geometry['segments']])
                if route:self.aux=h;path=route;break
        # Try a new control when the current learned model has no route.
        if path:
            idx=path[0];tag='compose_observed_click_effects'
            if self.visits[(pos,idx)]>=2:idx=None
        if idx is None:
            fresh=[i for i in range(len(s['buttons']))if self.tried[i]==0]
            if fresh:idx=fresh[0]
            else:
                choices=[]
                for i,d in self.models.items():
                    q=tuple(x+y for x,y in zip(pos,d));dist=sum(abs(x-y)for x,y in zip(q,target)if y is not None);choices.append((self.visits[(pos,i)],dist,i))
                if choices:idx=min(choices)[2];tag='revise_incomplete_effect_model'
        if intervention is not None:idx=intervention;tag='test_contextual_aperture_interaction'
        if idx is None or self.t>=512:return dict(done=True,action=None,data={})
        self.tried[idx]+=1;self.visits[(pos,idx)]+=1
        cert=dict(kind='coupled_marker_alignment',source=self.t,tag=tag,scene=s,prerequisite_hypothesis=copy.deepcopy(self.aux),tested_prerequisites=copy.deepcopy(self.probe_trials),geometry=copy.deepcopy(self.geometry),models=copy.deepcopy(self.models),evidence=copy.deepcopy(self.evidence),failures=copy.deepcopy(self.failures),archive=copy.deepcopy(self.archive),index=idx,plan=path,goal_role_is_hypothesis=True)
        self.previous=dict(source=self.t,scene=copy.deepcopy(s),index=idx);self.t+=1
        return dict(done=False,action=6,data=s['buttons'][idx]['point'],certificate=cert)
