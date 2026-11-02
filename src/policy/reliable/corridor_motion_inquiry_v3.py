"""Retain object motion while testing sustained horizontal actions after tile inquiry."""
import copy
from repeated_tile_inquiry_v1 import Agent as Prior
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.prior=Prior();self.color=None;self.shape=None;self.previous=None;self.last=None;self.direction=4;self.steps=0;self.effects=[];self.resets=0
 def actor(self,obs):
  ps=[p for p in parts(obs['frame']) if 8<=p['y']<60 and 3<=p['area']<=12 and p['h']<=5 and p['w']<=5]
  if self.color is None and ps:
   q=max(ps,key=lambda p:p['area']);self.color=q['color'];self.shape=q['shape']
  found=[p for p in ps if p['color']==self.color and (p['shape']==self.shape or tuple(sorted((a,p['w']-1-b) for a,b in p['shape']))==tuple(sorted(self.shape or ())))];return found[0] if len(found)==1 else None
 def respond(self,obs):
  actor=self.actor(obs)
  if self.previous is not None:
   event=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));old=self.actor(self.previous);delta=[actor[k]-old[k] for k in ['y','x']] if actor and old else None;self.effects.append(dict(source=digest(event),delta=delta))
   if delta==[0,0] and self.last['action'] in (3,4):self.direction=7-self.direction
  r=self.prior.respond(obs)
  if r['done']:
   a=None;cert=None
   if obs['state']=='GAME_OVER' and self.resets<1:self.resets+=1;a=0
   elif actor and obs['state']=='NOT_FINISHED' and self.steps<80:a=self.direction;self.steps+=1
   if a is not None:cert=dict(kind='corridor_motion_inquiry',context=digest(obs),action=a,actor=actor,effects=copy.deepcopy(self.effects),goal_is_hypothesis=True)
   r=dict(action=a,data={},done=a is None,certificate=cert,advisor='corridor_motion_inquiry',diagnostics=dict(steps=self.steps,direction=self.direction,resets=self.resets))
  self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r);self.prior.last=copy.deepcopy(r);return r
