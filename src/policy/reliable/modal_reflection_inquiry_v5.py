"""Learn mode-conditioned visual motion and bind goals to stationary matching shapes."""
import copy
from collections import Counter,deque
from modal_visible_parts_v1 import parts
from visual_transform_learner import digest

def signature(p):return tuple(map(tuple,p['shape']))
def mode(o,inks=None):return tuple(sorted((c,n)for c,n in Counter(p['color']for p in parts(o['frame'])if p['area']==1).items()if (n>=3 if inks is None else c in inks)))
def compatible(a,b):
 return a['color']==b['color']and a['h']==b['h']and a['w']==b['w']and abs(a['area']-b['area'])<=max(2,.1*max(a['area'],b['area']))
def same(a,b):return a['color']==b['color']and signature(a)==signature(b)and a['y']==b['y']and a['x']==b['x']
def plan(start,goal,models,switches,h,w,blocked=(),objects=None,limit=40000):
 objects=objects or {};keys=sorted(objects);initial=(start[0],start[1],start[2],tuple(objects[k]for k in keys));target=(goal['y'],goal['x']);todo=deque([initial]);parents={initial:None}
 while todo and len(parents)<limit:
  state=todo.popleft();m,y,x,positions=state
  if(y,x)==target:
   actions=[]
   while parents[state]is not None:state,a=parents[state];actions.append(a)
   return actions[::-1]
  edges=[]
  for a,q in models.get(m,{}).items():
   dy,dx=q['delta'];new=list(positions);valid=True
   for extra in q.get('coupled',[]):
    key=tuple(extra['key'])
    if key not in keys:continue
    i=keys.index(key);yy,xx=new[i];ddy,ddx=extra['delta'];yy+=ddy;xx+=ddx
    if not(0<=yy<=64-key[1]and 0<=xx<=64-key[2]):valid=False;break
    new[i]=(yy,xx)
   if valid:edges.append((a,(m,y+dy,x+dx,tuple(new))))
  for a,q in switches.get(m,{}).items():edges.append((a,(q['after_mode'],y,x,positions)))
  for a,t in edges:
   if((m,y,x),a)in blocked:continue
   if t in parents or not(0<=t[1]<=64-h and 0<=t[2]<=64-w):continue
   parents[t]=(state,a);todo.append(t)
 return None
class Agent:
 def __init__(self):self.active=True;self.level=None;self.t=0;self.previous=None;self.actor=None;self.goal=None;self.models={};self.switches={};self.tried=Counter();self.role_sources=[];self.knowledge=[];self.blocked=set();self.episode_steps=0;self.reset_attempts=0;self.failed_edges=set();self.failure_memory=[]
 def context(self,o):return mode(o,self.mode_inks)
 def answer(self,o,a,reason,extra=None):
  c=dict(kind='modal_reflection',source=self.t,context=digest(o),mode=self.context(o),mode_inks=self.mode_inks,actor=copy.deepcopy(self.actor),goal=copy.deepcopy(self.goal),models=copy.deepcopy(list((m,[(a,q)for a,q in actions.items()])for m,actions in self.models.items())),switches=copy.deepcopy(list((m,[(a,q)for a,q in actions.items()])for m,actions in self.switches.items())),role_sources=copy.deepcopy(self.role_sources),knowledge=copy.deepcopy(self.knowledge),failure_memory=copy.deepcopy(self.failure_memory),goal_is_hypothesis=True,reason=reason,**(extra or {}));r=dict(done=False,action=a,data={},certificate=c,advisor='modal_reflection_inquiry');self.previous=dict(raw=copy.deepcopy(o),r=copy.deepcopy(r),source=self.t);self.t+=1;self.episode_steps+=1;self.tried[self.context(o),a]+=1;return r
 def respond(self,o):
  if o['state']=='WIN':return dict(done=True,action=None,data={})
  if self.level!=o['levels_completed']:
   self.mode_inks=[c for c,n in mode(o)];self.level=o['levels_completed'];self.actor=None;self.goal=None;self.models={};self.switches={};self.tried=Counter();self.blocked=set();self.previous=None;self.episode_steps=0;self.failed_edges=set()
  ps=parts(o['frame']);current=self.context(o)
  if self.previous and self.previous['raw']['levels_completed']==self.level:
   old=self.previous;before=parts(old['raw']['frame']);oldmode=self.context(old['raw']);a=old['r']['action'];moves=[]
   for b in before:
    if b['area']<12 or any(same(b,q)for q in ps):continue
    matches=[q for q in ps if q['color']==b['color']and signature(q)==signature(b)]
    if len(matches)!=1:continue
    q=matches[0];goals=[g for g in ps if g['color']!=b['color']and signature(g)==signature(b)and any(same(g,v)for v in before)]
    if goals:moves.append((b['area'],b,q,goals[0]))
   if self.actor:
    bb=[b for b in before if compatible(b,self.actor)]
    qq=[q for q in ps if compatible(q,self.actor)]
    if len(bb)==len(qq)==1:
     b,q=bb[0],qq[0];self.actor=q
     dy,dx=q['y']-b['y'],q['x']-b['x']
     if abs(dy)+abs(dx)>0:
      self.models.setdefault(oldmode,{})[a]=dict(source=old['source'],before=b,after=q,delta=(dy,dx),mode=oldmode);self.knowledge.append(dict(source=old['source'],kind='observed_modal_translation'))
    moves=[]
   if moves:
    _,b,q,g=max(moves,key=lambda v:(v[0],-v[1]['color']));self.actor=q;self.goal=g;dy,dx=q['y']-b['y'],q['x']-b['x']
    if abs(dy)+abs(dx)>0:
     m=dict(source=old['source'],before=b,after=q,delta=(dy,dx),mode=oldmode);self.models.setdefault(oldmode,{})[a]=m;self.role_sources.append(dict(source=old['source'],moving_before=b,moving_after=q,stationary=g));self.knowledge.append(dict(source=old['source'],kind='observed_modal_translation'))
   elif self.actor:
    matches=[q for q in ps if q['color']==self.actor['color']and compatible(q,self.actor)]
    if len(matches)==1:self.actor=matches[0]
    if self.actor and old['r']['certificate'].get('actor')and self.actor['y']==old['r']['certificate']['actor']['y']and self.actor['x']==old['r']['certificate']['actor']['x']:self.blocked.add((digest(old['raw']),a))
   if oldmode!=current and self.actor and old['r']['certificate'].get('actor')and same(self.actor,old['r']['certificate']['actor']):
    self.switches.setdefault(oldmode,{})[a]=dict(source=old['source'],before_mode=oldmode,after_mode=current);self.knowledge.append(dict(source=old['source'],kind='observed_control_context_change'))
   for model in self.models.get(oldmode,{}).values():
    if model['source']!=old['source']:continue
    model['coupled']=[]
    for b in before:
     if b['area']<12 or(self.actor and b['color']==self.actor['color']):continue
     matches=[q for q in ps if compatible(b,q)]
     if len(matches)!=1:continue
     q=matches[0];dy,dx=q['y']-b['y'],q['x']-b['x']
     if dy or dx:model['coupled'].append(dict(key=(b['color'],b['h'],b['w']),before=b,after=q,delta=(dy,dx)))
   prior_actor=old['r']['certificate'].get('actor')
   if self.actor and prior_actor and oldmode==current and same(self.actor,prior_actor)and a in self.models.get(oldmode,{}):
    self.failed_edges.add(((oldmode,prior_actor['y'],prior_actor['x']),a));self.failure_memory.append(dict(source=old['source'],mode=oldmode,actor=prior_actor,action=a,kind='observed_blocked_control'))
   if self.goal:
    goals=[g for g in ps if same(g,self.goal)]
    if goals:self.goal=goals[0]
  if self.episode_steps>=220 or o['state']!='NOT_FINISHED':return dict(done=True,action=None,data={})
  allowed=[a for a in o['available_actions']if a in(1,2,3,4,5)]
  if self.actor and self.goal:
   keys={tuple(q['key'])for actions in self.models.values()for model in actions.values()for q in model.get('coupled',[])};objects={}
   for key in keys:
    matches=[p for p in ps if(p['color'],p['h'],p['w'])==key]
    if len(matches)==1:objects[key]=(matches[0]['y'],matches[0]['x'])
   route=plan((current,self.actor['y'],self.actor['x']),self.goal,self.models,self.switches,self.actor['h'],self.actor['w'],self.failed_edges,objects)
   if route and(digest(o),route[0])not in self.blocked:return self.answer(o,route[0],'test_learned_modal_goal_route',dict(route=route))
  unknown=[a for a in allowed if self.tried[current,a]==0]
  if unknown:return self.answer(o,min(unknown),'identify_conditional_control')
  # Test another visible mode before repeating a refuted positional approach.
  changes=[a for a in self.switches.get(current,{})if(digest(o),a)not in self.blocked]
  if changes:return self.answer(o,min(changes),'retrieve_alternative_control_context')
  return dict(done=True,action=None,data={})
