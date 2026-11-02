"""Discriminate a demonstrated displacement from the true click-range boundary."""
import copy
from waypoint_recursive_inquiry_v15 import Agent as Prefix
from waypoint_failure_recovery_v1 import composition,board_digest
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.prefix=Prefix();self.stage=0;self.trial=None;self.results=[];self.origin=None;self.start=None;self.saved=None;self.deferred=None;self.pending_observation=None
 def respond(self,obs):
  if self.stage==0:
   r=self.prefix.respond(obs);scene=composition(obs);tokens=scene['tokens'];motion=self.prefix.prior.prior.motion
   large=[p for p in tokens if p['h']==3];reach=max([max(abs(v)for v in q['delta'])for q in motion]or[0])
   if not r['done']and obs['state']=='NOT_FINISHED'and 7 in obs['available_actions']and len(scene['palette'])>=3 and len(large)==1 and reach>=6:
    self.deferred=copy.deepcopy(r);self.origin=large[0];self.start=copy.deepcopy(obs);self.saved=copy.deepcopy(motion);return self.propose(obs,2*reach)
   return r
  if self.stage in(1,3):
   before=self.trial;scene=composition(obs);new=[p for p in scene['tokens']if p['color']==self.origin['color']and p['h']==self.origin['h']];point=before['point'];matched=next((p for p in new if[p['y']+p['h']//2,p['x']+p['w']//2]==list(point)),None)
   result=dict(event_source=digest(dict(before=self.pending_observation,action=6,data=dict(y=point[0],x=point[1]),after=obs)),trial=copy.deepcopy(before),after_tokens=copy.deepcopy(new),reached=matched is not None,after_context=digest(obs));self.results.append(result);self.stage+=1
   return dict(done=False,action=7,data={},certificate=dict(kind='waypoint_range_inquiry',context=digest(obs),tag='undo_range_inquiry',trial=copy.deepcopy(before),outcomes=copy.deepcopy(self.results)),advisor='waypoint_range_inquiry',diagnostics=dict(reason='undo_range_inquiry'))
  if self.stage in(2,4):
   restored=board_digest(obs)==board_digest(self.start)
   if self.stage==4 or not restored:return dict(done=True,action=None,data={},certificate=None,advisor='waypoint_range_inquiry',diagnostics=dict(reason='range_trials_complete',outcomes=self.results,restored=restored))
   reach=max(max(abs(v)for v in q['delta'])for q in self.saved);return self.propose(obs,3*reach if self.results[-1]['reached']else reach+reach//2)
  return dict(done=True,action=None,data={},certificate=None,advisor='waypoint_range_inquiry',diagnostics=dict(reason='no_probe'))
 def propose(self,obs,distance):
  scene=composition(obs);p=self.origin;origin=(p['y']+p['h']//2,p['x']+p['w']//2);choices=[]
  for dy,dx in[(-distance,0),(0,distance),(0,-distance),(distance,0)]:
   point=(origin[0]+dy,origin[1]+dx)
   if not(10<=point[0]<=60 and 2<=point[1]<=61):continue
   if any((point[0]-q['y']-q['h']//2)**2+(point[1]-q['x']-q['w']//2)**2<=distance**2 for q in scene['tokens']if q!=p):continue
   choices.append((point[0],abs(point[1]-32),point))
  if not choices:return dict(done=True,action=None,data={},certificate=None,advisor='waypoint_range_inquiry',diagnostics=dict(reason='no_unambiguous_range_probe'))
  point=min(choices)[2];self.pending_observation=copy.deepcopy(obs);self.trial=dict(context=digest(obs),actor=copy.deepcopy(p),point=point,distance=distance,reach_evidence=copy.deepcopy(self.saved));self.stage+=1
  return dict(done=False,action=6,data=dict(y=point[0],x=point[1]),certificate=dict(kind='waypoint_range_inquiry',context=digest(obs),tag='test_axis_range_beyond_demonstrated_displacement',trial=copy.deepcopy(self.trial),outcomes=copy.deepcopy(self.results)),advisor='waypoint_range_inquiry',diagnostics=dict(reason='test_axis_range_beyond_demonstrated_displacement'))
