import copy
from typed_viewport_peg_learning_v4 import Agent as Prefix
from viewport_peg_learning_v10 import Agent as Core
from peg_world_memory_v13 import Memory
from decorated_peg_carrier_v1 import carriers
class Agent:
 def __init__(self,prior=None):self.prior=prior;self.active=True;self.prefix=Prefix();self.core=None;self.trial=None;self.attempted=False
 def respond(self,raw):
  if self.core and self.trial:
   m=self.core.memory;v=m.observe(raw,self.core.t);p=self.trial;self.trial=None
   expected=tuple(p['position'][j]+p['delta'][j]for j in(0,1))
   if not v or expected not in v['positions']or expected not in set(v['layout']['pivots']):return dict(done=True,action=None,data={})
   m.movable_pivot_rules.append(dict(source=p['source'],before=p['position'],after=expected,delta=p['delta'],action=p['action'],hypothesis='retained_token_moves_with_observed_carrier_control'))
   return self.core.respond(raw)
  if self.core:return self.core.respond(raw)
  r=self.prefix.respond(raw)
  if not r['done']or self.attempted or not self.prefix.learner or raw['state']!='NOT_FINISHED':return r
  self.attempted=True;old=self.prefix.learner;m=Memory();m.__dict__.update(copy.deepcopy(old.memory.__dict__));m.movable_pivot_rules=[]
  bodies=carriers(raw['frame'],m.template,m.permanent_rules)
  if not bodies:return r
  v=m.observe(raw,old.t)
  if not v:return r
  candidates=[]
  for b in bodies:
   p=(b['box'][0]+1+m.camera[0],b['box'][1]+1+m.camera[1])
   for delta,action in sorted(old.controls.items()):
    if tuple(p[j]+delta[j]for j in(0,1))in set(v['layout']['rails']):candidates.append((p,delta,action,b))
  if not candidates:return r
  p,delta,action,b=min(candidates);self.core=Core();self.core.__dict__.update(copy.deepcopy(old.__dict__));self.core.memory=m;self.core.previous=None;self.core.retained_plan=None
  self.trial=dict(source=old.t,position=p,delta=delta,action=action)
  cert=dict(kind='decorated_peg_carrier_inquiry',source=old.t,body=b,template=copy.deepcopy(m.template),rule=next(r for r in m.permanent_rules if r['source']==b['pivot_rule_source']),position=p,camera=m.camera,delta=delta,action=action,controls=[dict(delta=d,action=a)for d,a in sorted(old.controls.items())],goal_is_hypothesis=True)
  self.core.t+=1;return dict(done=False,action=action,data={},certificate=cert)
