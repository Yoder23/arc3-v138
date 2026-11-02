"""Use measured full-scene effects to move barriers and satisfy multiple endpoints."""
import copy,heapq,itertools
from chain_endpoint_inquiry_v2 import Agent as Prior
from multi_endpoint_scene_v5 import scene,key,valid
from visual_transform_learner import digest

def plan(sc,models):
 n=len(sc['ends']);gs=sc['goals']
 if len(gs)!=n:return None
 goals=[tuple(v for p in q for v in p) for q in itertools.permutations(gs)];offset=len(sc['state'])-2*n
 def h(s):return min(sum(abs(a-b) for a,b in zip(s[offset:],g))/3 for g in goals)
 start=tuple(sc['state']);q=[(2*h(start),0,start,[])];cost={start:0};expanded=0
 while q and expanded<50000:
  _,g,s,path=heapq.heappop(q)
  if g!=cost[s]:continue
  expanded+=1
  if s[offset:] in goals:return path
  for k,m in sorted(models.items()):
   if len(m['support'])<2:continue
   ns=tuple(a+b for a,b in zip(s,m['delta']))
   if cost.get(ns,10**9)<=g+1 or not valid(ns,sc):continue
   cost[ns]=g+1;heapq.heappush(q,(g+1+2*h(ns),g+1,ns,path+[k]))
 return None
class Agent:
 def __init__(self):self.prior=Prior();self.active=False;self.level=None;self.models={};self.tried={};self.pending=None;self.steps=0;self.failures=[];self.memory=[];self.templates=None;self.roles=None
 def respond(self,o):
  sc=scene(o,self.templates if self.level==o['levels_completed'] else None,self.roles if self.level==o['levels_completed'] else None)
  if self.level!=o['levels_completed']:
   self.level=o['levels_completed'];self.memory.append(copy.deepcopy(self.models));self.models={};self.tried={};self.pending=None;self.steps=0;self.active=bool(sc and len(sc['goals'])>=2);self.templates=copy.deepcopy(sc['templates']) if sc else None;self.roles=copy.deepcopy(sc['roles']) if sc else None
   if self.active:self.prior.previous=None;self.prior.pending=None;self.prior.prior.previous=None;self.prior.prior.pending=None
  if not self.active:return self.prior.respond(o)
  if not sc or o['state']!='NOT_FINISHED':return dict(action=None,data={},done=True,certificate=None,advisor='multi_endpoint',diagnostics=dict(reason='unresolved_scene'))
  if self.pending:
   before,old,p=self.pending;src=digest(dict(before=before,action=6,data=dict(y=p['y']+1,x=p['x']+1),after=o));delta=[b-a for a,b in zip(old['state'],sc['state'])];k=key(p)
   if len(delta)==len(sc['state']) and any(delta):
    if k not in self.models or self.models[k]['delta']!=delta:self.models[k]=dict(delta=delta,support=[])
    self.models[k]['support'].append(dict(source=src,before=old,after=sc,button=p))
   else:self.failures.append(dict(source=src,button=p))
  self.pending=None;p=None;path=None
  if self.steps<160:
   candidates=[p for p in sc['buttons'] if self.tried.get(key(p),0)<1]
   if candidates:p=candidates[0]
   else:
    path=plan(sc,self.models)
    if path:p=next(p for p in sc['buttons'] if key(p)==path[0])
    else:
     candidates=[p for p in sc['buttons'] if len(self.models.get(key(p),{}).get('support',[]))<2 and self.tried.get(key(p),0)<5]
     if candidates:p=min(candidates,key=lambda p:(self.tried.get(key(p),0),key(p)))
  cert=None;data={};a=None
  if p:
   a=6;data=dict(y=p['y']+1,x=p['x']+1);self.tried[key(p)]=self.tried.get(key(p),0)+1;self.steps+=1;cert=dict(kind='multiple_endpoint_composition',context=digest(o),action=a,scene=sc,button=p,models=copy.deepcopy(self.models),path=path,failures=copy.deepcopy(self.failures),goal_is_hypothesis=True);self.pending=(copy.deepcopy(o),copy.deepcopy(sc),copy.deepcopy(p))
  return dict(action=a,data=data,done=a is None,certificate=cert,advisor='multi_endpoint',diagnostics=dict(reason='learn_panel_motion_and_compose_all_endpoints',steps=self.steps,models=len(self.models)))
