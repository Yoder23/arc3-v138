"""Bounded interface inquiry when a new scene hides the previously tracked actor."""
import copy
from waypoint_action_learner_v2 import Agent as Prior
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.prior=Prior();self.tried={};self.steps=0;self.sources=[]
 def respond(self,obs):
  r=self.prior.respond(obs)
  if not r['done'] or obs['state']!='NOT_FINISHED':return r
  tried=self.tried.setdefault(obs['levels_completed'],set());action=None;data={};point=None;reason='unresolved_interface'
  if self.steps<16:
   if 7 in obs['available_actions'] and ('action',7) not in tried:action=7;tried.add(('action',7));reason='test_simple_action_when_actor_not_visible'
   else:
    ps=parts(obs['frame']);candidates=[]
    for p in ps:
     if p['area']==4 and p['h']==p['w']==2 and p['y']<8:candidates.append((0,p['x'],(p['y']+1,p['x']+1)))
     elif p['area']==1 and p['y']>=8:candidates.append((1,p['y'],(p['y'],p['x'])))
    options=[p for _,_,p in sorted(candidates) if p not in tried]
    if options:point=options[0];action=6;data=dict(y=point[0],x=point[1]);tried.add(point);reason='test_visible_interface_or_waypoint'
  cert=None
  if action is not None:
   self.steps+=1;cert=dict(kind='waypoint_interface_probe',context=digest(obs),action=action,click=point,pixel=None if point is None else obs['frame'][point[0]][point[1]],interpretation='bounded_interface_hypothesis')
  r=dict(action=action,data=data,done=action is None,certificate=cert,advisor='waypoint_scene_inquiry',diagnostics=dict(reason=reason,probes=self.steps,retained_motion=len(self.prior.motion),failed_attempts=len(self.prior.failures)));self.prior.last=copy.deepcopy(r);return r
