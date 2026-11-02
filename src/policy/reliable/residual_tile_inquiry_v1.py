"""Test a residual visible symbol after a tile interaction, retaining real action history."""
import copy
from clearance_route_inquiry_v11 import Agent as Prior
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.prior=Prior();self.previous=None;self.last=None;self.tried=set();self.probes=0
 def respond(self,obs):
  response=self.prior.respond(obs);old=self.last;tile=(old.get('certificate') or {}).get('tile') if old else None
  if tile and old['action']==6 and self.previous['levels_completed']==obs['levels_completed'] and obs['state']=='NOT_FINISHED' and self.probes<12:
   y,x=old['data']['y'],old['data']['x'];points=[(yy,xx) for yy in range(tile['y'],tile['y']+tile['h']) for xx in range(tile['x'],tile['x']+tile['w']) if obs['frame'][yy][xx]==tile['color']];key=(obs['levels_completed'],tile['color'],y,x,tuple(points));event=dict(before=self.previous,action=old['action'],data=old['data'],after=copy.deepcopy(obs))
   if 3<=len(points)<=8 and key not in self.tried:
    self.tried.add(key);self.probes+=1;cert=dict(kind='residual_tile_probe',context=digest(obs),action=6,source=digest(event),tile=tile,points=points,click=(y,x),interpretation='test_residual_symbol_after_partial_tile_removal');response=dict(action=6,data=dict(y=y,x=x),done=False,certificate=cert,advisor='residual_tile_inquiry',diagnostics=dict(reason='test_residual_interaction_instead_of_assuming_empty_space',probes=self.probes));self.prior.last=copy.deepcopy(response)
  self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(response);return response
