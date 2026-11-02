import copy
from moving_pivot_peg_learning_v2 import Agent as Prefix
from rare_actor_jump_geometry_v1 import proposals
class Agent:
 def __init__(self,prior=None):self.prior=prior;self.active=True;self.prefix=Prefix();self.t=0;self.trial=None;self.stage='select';self.selected=None;self.outcomes=[];self.previous=None
 def respond(self,raw):
  if self.trial is None:
   r=self.prefix.respond(raw)
   if not r['done']:self.t+=1;return r
   if raw['state']!='NOT_FINISHED':return r
   choices=proposals(raw['frame'])
   if not choices:return r
   self.trial=dict(choices[0],source=self.t,level=raw['levels_completed'])
  p=self.trial
  if self.previous:
   self.outcomes.append(dict(self.previous,after=copy.deepcopy(raw)));self.previous=None
  if self.stage=='done'or raw['levels_completed']!=p['level']:return dict(done=True,action=None,data={},certificate=dict(rare_actor_trial=p,outcomes=self.outcomes))
  size=p['scene']['size'];k=(size-1)//2
  if self.stage=='select':self.selected=copy.deepcopy(raw);self.stage='land';target=p['jump'][0];tag='select_rare_actor_with_ordinary_neighbor'
  else:
   self.stage='done';target=p['jump'][2];a=self.selected['frame'];b=raw['frame']
   if not any(a[y][x]!=b[y][x]for y in range(target[0],target[0]+size)for x in range(target[1],target[1]+size)):return dict(done=True,action=None,data={},certificate=dict(rare_actor_trial=p,outcomes=self.outcomes,no_highlight=True))
   tag='test_highlighted_rare_actor_jump'
  data=dict(x=target[1]+k,y=target[0]+k);c=dict(kind='rare_actor_jump_inquiry',source=self.t,tag=tag,trial=copy.deepcopy(p),outcomes=copy.deepcopy(self.outcomes))
  self.previous=dict(source=self.t,action=6,data=data,before=copy.deepcopy(raw));self.t+=1
  return dict(done=False,action=6,data=data,certificate=c)
