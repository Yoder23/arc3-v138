"""Retain successful click displacements and test local waypoint alternatives after failure."""
import copy
from collections import Counter
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest

def scene(obs):
 ps=parts(obs['frame']);dots=[p for p in ps if p['area']==1 and p['y']>=8];counts=Counter(p['color'] for p in dots);color=max(counts,key=counts.get) if counts else None
 points=[(p['y'],p['x']) for p in dots if p['color']==color];goals=[(p['y']+1,p['x']+1) for p in ps if p['color']==color and p['area']==9 and p['h']==p['w']==3 and p['y']>=8]
 actors=[dict(color=p['color'],point=(p['y']+1,p['x']+1)) for p in ps if p['color']!=color and p['area']==9 and p['h']==p['w']==3 and p['y']>=8]
 crosses=[(p['y']+1,p['x']+1) for p in ps if p['area']==5 and p['h']==p['w']==3 and p['y']>=8]
 return actors,sorted(set(points+crosses+goals)),goals,color
class Agent:
 def __init__(self):self.previous=None;self.last=None;self.motion=[];self.failures=[];self.tried={};self.level=None;self.actor_color=None;self.history={};self.steps=0
 def respond(self,obs):
  if self.previous is not None:
   e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));h=digest(e);self.history[h]=e
   if self.last['action']==6 and self.previous['levels_completed']==obs['levels_completed']:
    before=scene(self.previous)[0];after=scene(obs)[0];lost=[a for a in before if a not in after];added=[b for b in after if b not in before];moved=[(a,b) for a in lost for b in added if len(lost)==len(added)==1 and a['color']==b['color'] and list(b['point'])==[self.last['data']['y'],self.last['data']['x']]]
    if len(moved)==1:
     a,b=moved[0];self.actor_color=b['color'];self.motion.append(dict(source=h,color=b['color'],origin=a['point'],destination=b['point'],delta=tuple(b['point'][i]-a['point'][i] for i in (0,1))))
    else:self.failures.append(dict(source=h,click=(self.last['data']['y'],self.last['data']['x']),reason='requested_actor_displacement_not_observed'))
  actors,points,goals,waypoint_color=scene(obs)
  if self.level!=obs['levels_completed']:self.level=obs['levels_completed'];self.tried={}
  actor=next((a for a in actors if a['color']==self.actor_color),actors[0] if len(actors)==1 else None);action=None;data={};cert=None;reason='unresolved_waypoint_scene'
  if obs['state']=='GAME_OVER':action=0;reason='retry_after_terminal_failure'
  elif obs['state']=='WIN':reason='WIN'
  elif actor and goals and self.steps<160:
   at=actor['point'];key=(self.level,at);tried=self.tried.setdefault(key,set());maxstep=max([max(abs(v) for v in p['delta']) for p in self.motion] or [8]);options=[]
   for p in points:
    if p==at or p in tried or max(abs(p[i]-at[i]) for i in (0,1))>maxstep:continue
    distance=min(sum(abs(p[i]-g[i]) for i in (0,1)) for g in goals);options.append((distance,-max(abs(p[i]-at[i]) for i in (0,1)),p))
   if options:
    _,_,p=min(options);tried.add(p);action=6;data=dict(y=p[0],x=p[1]);reason='test_retained_local_click_reach';self.steps+=1;cert=dict(kind='waypoint_displacement_hypothesis',context=digest(obs),action=6,actor=actor,destination=p,waypoint_color=waypoint_color,goals=goals,points=points,range_hypothesis=maxstep,motion=copy.deepcopy(self.motion),failures=copy.deepcopy(self.failures),goal_is_hypothesis=True)
  r=dict(action=action,data=data,done=action is None,certificate=cert,advisor='waypoint_action_learner',diagnostics=dict(reason=reason,retained_motion=len(self.motion),failed_attempts=len(self.failures),steps=self.steps));self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r);return r
