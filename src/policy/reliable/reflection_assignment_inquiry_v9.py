import copy
from collections import Counter,deque
from modal_reflection_inquiry_v5 import Agent as Base
from modal_scene_v7 import objects,shape,context
from reflection_goal_assignment_v6 import infer,axes
from reflection_axes_v2 import position as axis_position,target as axis_target
from audit_connector_frames_portable_v1 import digest
def body_route(body,goal,models,others,limit=10000):
 start=(body['y'],body['x']);target=(goal['y'],goal['x']);blocked=set()
 for p in others:
  for dy,dx in shape(p):
   y,x=p['y']+dy,p['x']+dx
   blocked.update((y+dy,x+dx)for dy in(-1,0,1)for dx in(-1,0,1))
 q=deque([start]);prev={start:None}
 while q and len(prev)<limit:
  pos=q.popleft()
  if pos==target:
   route=[]
   while prev[pos]is not None:pos,a=prev[pos];route.append(a)
   return route[::-1]
  for a,m in models.items():
   dy,dx=m['delta'];new=(pos[0]+dy,pos[1]+dx)
   if new in prev or not(0<=new[0]<=64-body['h']and 0<=new[1]<=64-body['w']):continue
   if any((new[0]+y,new[1]+x)in blocked for y,x in shape(body)):continue
   prev[new]=(pos,a);q.append(new)
 return None
class Agent:
 def __init__(self):self.active=True;self.base=Base();self.level=None;self.assignment=None;self.t=0;self.knowledge=[];self.failed=[];self.previous=None;self.models={};self.tried=Counter();self.assignment_source=None;self.skill_bank={};self.erase_skill_retrieval=False
 def respond(self,o):
  if o['state']!='NOT_FINISHED':return dict(done=True,action=None,data={})
  if self.level!=o['levels_completed']:
   self.level=o['levels_completed'];self.assignment=infer(o);self.assignment_source=self.t;self.previous=None;self.models={};self.tried=Counter()
  if self.assignment is None:
   self.base.t=self.t;r=self.base.respond(o);self.t=self.base.t;return r
  ass=self.assignment;mode=context(o,ass['marker']);ps=objects(o);axis=next((a for a in axes(o)if a['ink']==ass['axis']['ink']),None)
  if axis is None:return dict(done=True,action=None,data={})
  selected=None
  for pair in ass['pairs']:
   b=pair['body'];matches=[p for p in ps if p['color']==b['color']and shape(p)==shape(b)]
   if len(matches)==1:
    p=matches[0]
    if len(mode)>3 and mode[0]==p['color']and mode[1:3]==(p['h'],p['w'])and mode[3]==shape(p):selected=(p,pair['goal'])
  is_axis=mode[:2]==(axis['ink'],'axis');position=axis_position(axis)if is_axis else(selected[0]['y'],selected[0]['x'])if selected else None
  skill=('axis',ass['axis']['axis'],mode[2]if len(mode)>2 else'one')if is_axis else('body',)if selected else None
  if skill and not self.erase_skill_retrieval:
   for a,model in self.skill_bank.get(skill,{}).items():
    if a not in self.models.setdefault(mode,{}):self.models[mode][a]=dict(**model,transferred=True,skill=skill)
  if self.previous:
   old=self.previous
   if mode==old['mode']and position is not None and old['position']is not None:
    delta=(position[0]-old['position'][0],position[1]-old['position'][1])
    if any(delta):
     model=dict(delta=delta,source=old['source']);self.models.setdefault(mode,{})[old['action']]=model
     if skill:self.skill_bank.setdefault(skill,{})[old['action']]=model
     self.knowledge.append(dict(source=old['source'],kind='observed_selected_object_translation',mode=mode,delta=delta,skill=skill))
    elif old['action']!=5:self.failed.append(dict(source=old['source'],mode=mode,position=position,action=old['action']))
  target=axis_target(ass)if is_axis else(selected[1]['y'],selected[1]['x'])if selected else None
  a=None;reason=None;route=None;others=[]
  if position is not None and target is not None and position!=target:
   options=[]
   for action,m in self.models.get(mode,{}).items():
    dy,dx=m['delta'];new=(position[0]+dy,position[1]+dx);distance=abs(new[0]-target[0])+abs(new[1]-target[1]);current=abs(position[0]-target[0])+abs(position[1]-target[1])
    if distance<current and not any(f['mode']==mode and f['position']==position and f['action']==action for f in self.failed):options.append((distance,action))
   if selected:
    others=[p for p in ps if p['color']==ass['body_ink']and p!=selected[0]]
    route=body_route(selected[0],selected[1],self.models.get(mode,{}),others)
    options=[(len(route),route[0])]if route else []
   if options:a=min(options)[1];reason='test_learned_control_toward_joint_goal'
   else:
    unknown=[a for a in(1,2,3,4)if a in o['available_actions']and self.tried[mode,a]==0]
    if unknown:a=min(unknown);reason='identify_selected_object_control'
  if a is None and 5 in o['available_actions']and self.tried[mode,5]<8:a=5;reason='select_next_goal_bound_object'
  if a is None:return dict(done=True,action=None,data={})
  c=dict(kind='reflection_assignment',source=self.t,context=digest(o),assignment_source=self.assignment_source,assignment=copy.deepcopy(ass),mode=mode,selected=selected,axis=axis,position=position,target=target,models=[dict(mode=m,action=a,**v)for m,actions in self.models.items()for a,v in actions.items()],knowledge=copy.deepcopy(self.knowledge),failures=copy.deepcopy(self.failed),reason=reason,avoidance_objects=others,route=route,skill_bank=[dict(skill=k,actions=list(v.items()))for k,v in self.skill_bank.items()],skill=skill,retrieval_ablated=self.erase_skill_retrieval,geometry_is_hypothesis=True)
  r=dict(done=False,action=a,data={},certificate=c,advisor='reflection_goal_assignment');self.previous=dict(raw=copy.deepcopy(o),mode=mode,position=position,action=a,source=self.t);self.t+=1;self.tried[mode,a]+=1;return r
