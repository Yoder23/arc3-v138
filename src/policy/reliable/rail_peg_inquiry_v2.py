import copy
from collections import Counter
from peg_jump_inquiry_v2 import Agent as Peg
from rail_peg_model_v1 import layout,carrier,occupancy,search
class Agent:
 def __init__(self,prior=None):self.prior=prior;self.active=True;self.peg=Peg();self.level=None;self.L=None;self.t=0;self.previous=None;self.motion_memory=[];self.controls={};self.probes=Counter();self.selected=None;self.rule_memory=[];self.failed_plans=[]
 def respond(self,raw):
  if self.L is None:
   candidate=layout(raw['frame']) if raw['levels_completed']!=self.peg.level else None
   if candidate and self.peg.rule_memory:
    self.L=candidate;self.level=raw['levels_completed'];self.t=self.peg.t;self.rule_memory=copy.deepcopy(self.peg.rule_memory);self.L['source']=self.t
   else:return self.peg.respond(raw)
  if raw['state']!='NOT_FINISHED':return dict(done=True,action=None,data={})
  if raw['levels_completed']!=self.level:
   self.level=raw['levels_completed'];self.L=layout(raw['frame']);self.controls={};self.probes=Counter();self.selected=None;self.previous=None
   if self.L:self.L['source']=self.t
   else:return dict(done=True,action=None,data={})
  o=carrier(raw['frame'],self.L['scene']['size'])
  if not o and self.selected and self.previous:
   y,x=self.previous['pos'];y-=1;x-=1;size=self.L['scene']['size']+2;ink=self.L['carrier']['ink'];corners=[(0,0),(0,size-1),(size-1,0),(size-1,size-1)]
   if all(raw['frame'][y+dy][x+dx]==ink for dy,dx in corners):o=dict(ink=ink,box=(y,x,size,size),shape=corners,occlusion_hypothesis='selection_overlay_preserves_carrier_corners')
  if not o:return dict(done=True,action=None,data={})
  pos=(o['box'][0]+1,o['box'][1]+1);marks=occupancy(raw['frame'],self.L,pos)
  if self.previous and self.previous['action']!=6:
   p=self.previous;delta=pos[0]-p['pos'][0],pos[1]-p['pos'][1]
   if delta!=(0,0):self.controls[delta]=p['action'];self.motion_memory.append(dict(source=p['source'],action=p['action'],before=p['pos'],after=pos,delta=delta))
  extra={};action=None;data={};tag=''
  unknown=[a for a in raw['available_actions']if a in (1,2,3,4) and self.probes[a]==0]
  if unknown:action=unknown[0];self.probes[action]+=1;tag='inquire_rail_control'
  elif self.selected:
   a,b,c=self.selected;data=self.point(c);action=6;tag='test_joint_jump_landing';extra['jump']=self.selected;self.selected=None
  else:
   plan,n=search(self.L,pos,marks)
   if not plan:return dict(done=True,action=None,data={})
   e=plan[0];extra=dict(joint_plan=plan,search_nodes=n)
   if e['steps']:
    delta=tuple(e['steps'][0]);action=self.controls.get(delta)
    if action is None:
     # Conventional directional order is only a proposal until actual displacement confirms it.
     pitch=self.L['scene']['pitch'];action={(-pitch,0):1,(pitch,0):2,(0,-pitch):3,(0,pitch):4}[delta];extra['unverified_control_hypothesis']=dict(action=action,delta=delta)
    tag='move_carrier_for_jump'
   else:
    self.selected=e['jump'];action=6;data=self.point(e['jump'][0]);tag='select_joint_jump'
  c=dict(kind='rail_peg_inquiry',source=self.t,layout=copy.deepcopy(self.L),carrier=copy.deepcopy(o),position=pos,marks=sorted(marks),motion_memory=copy.deepcopy(self.motion_memory),rule_memory=copy.deepcopy(self.rule_memory),tag=tag,goal_is_hypothesis=True,**extra)
  self.previous=dict(source=self.t,pos=pos,action=action);self.t+=1;return dict(done=False,action=action,data=data,certificate=c)
 def point(self,p):k=(self.L['scene']['size']-1)//2;return dict(x=p[1]+k,y=p[0]+k)
