import copy
from waypoint_range_inquiry_v2 import Agent as Inquiry
from waypoint_measured_backtracking_v3 import Agent as Planner
from waypoint_failure_recovery_v1 import board_digest
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.inquiry=Inquiry();self.planner=None;self.t=0
 def respond(self,obs):
  if self.planner:return self.planner.respond(obs)
  r=self.inquiry.respond(obs)
  if not r['done']:self.t+=1;return r
  good=[q for q in self.inquiry.results if q['reached']]
  if not good or self.inquiry.stage!=4 or board_digest(obs)!=board_digest(self.inquiry.start):return r
  best=max(good,key=lambda q:q['trial']['distance']);p=best['trial'];support=dict(source=best['event_source'],actor=p['actor'],point=p['point'],distance=p['distance'],hypothesis='conservative_radial_planning_bound_from_observed_axis_motion')
  a=Planner();a.prefix=self.inquiry.prefix;a.range_support=support;a.level=obs['levels_completed'];a.t=self.t
  response=copy.deepcopy(self.inquiry.deferred)
  if response.get('certificate'):response['certificate']['context']=digest(obs)
  a.prefix.previous=copy.deepcopy(obs);a.prefix.last=copy.deepcopy(response);a.prefix.prior.prior.previous=copy.deepcopy(obs);a.prefix.prior.prior.last=copy.deepcopy(response)
  self.planner=a;return a.emit(obs,response)
