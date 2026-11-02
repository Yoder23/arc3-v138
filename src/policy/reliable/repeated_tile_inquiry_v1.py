"""Test a repeated visible interaction motif and retain actual disappearance evidence."""
import copy
from collections import Counter
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.level=None;self.tried=set();self.signature=None;self.previous=None;self.last=None;self.effects=[];self.steps=0
 def respond(self,obs):
  if self.previous is not None:
   e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));self.effects.append(dict(source=digest(e),changed_pixels=sum(a!=b for r,s in zip(self.previous['frame'][:62],obs['frame'][:62]) for a,b in zip(r,s)),progress=obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN'))
  if self.level!=obs['levels_completed']:self.level=obs['levels_completed'];self.tried=set();self.signature=None
  ps=[p for p in parts(obs['frame']) if 3<=p['h']<=7 and 3<=p['w']<=7 and p['area']>=8];groups=Counter((p['color'],p['h'],p['w'],p['shape']) for p in ps)
  if self.signature is None and groups:
   signature,n=groups.most_common(1)[0]
   if n>=3:self.signature=signature
  options=[p for p in ps if (p['color'],p['h'],p['w'],p['shape'])==self.signature and (p['y'],p['x']) not in self.tried];a=None;data={};c=None
  if options and self.steps<80 and obs['state']=='NOT_FINISHED':
   p=min(options,key=lambda p:(p['y'],p['x']));point=(p['y']+p['h']//2,p['x']+p['w']//2);self.tried.add((p['y'],p['x']));self.steps+=1;a=6;data=dict(y=point[0],x=point[1]);c=dict(kind='repeated_tile_inquiry',context=digest(obs),action=a,object=p,effects=copy.deepcopy(self.effects),goal_is_hypothesis=True)
  r=dict(action=a,data=data,done=a is None,certificate=c,advisor='repeated_tile_inquiry',diagnostics=dict(steps=self.steps,retained_outcomes=len(self.effects)));self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r);return r
