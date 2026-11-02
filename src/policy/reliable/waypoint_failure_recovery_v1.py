"""Retain harmful click outcomes, test rollback, and try untried alternatives."""
import copy
from waypoint_recursive_inquiry_v15 import Agent as Prefix
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
def board_digest(obs):return digest(obs['frame'][8:62])
def composition(obs):
 ps=parts(obs['frame']);palette=sorted({p['color']for p in ps if p['y']<3 and p['h']==p['w']==2 and p['area']==4})
 tokens=[{k:p[k]for k in('color','y','x','h','w','area')}for p in ps if p['y']>=8 and p['h']==p['w']and p['area']==p['h']**2 and 1<=p['h']<=5 and p['color']in palette]
 return dict(palette=palette,tokens=tokens,mass=sum(2**(p['h']-1)for p in tokens))
class Agent:
 def __init__(self):self.prefix=Prefix();self.previous=None;self.last=None;self.pending=None;self.failures=[];self.rollbacks=[];self.attempts={};self.disabled=False;self.active=True
 def respond(self,obs):
  event=None
  if self.previous is not None:event=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs))
  if self.pending:
   restored=board_digest(obs)==self.pending['expected_board']and obs['levels_completed']==self.pending['level']
   self.rollbacks.append(dict(source=digest(event),failure_source=self.pending['source'],restored=restored,expected_board=self.pending['expected_board'],observed_board=board_digest(obs)))
   if not restored:self.disabled=True
   self.pending=None
  r=self.prefix.respond(obs);level=obs['levels_completed'];old=composition(self.previous)if self.previous else None;now=composition(obs)
  hazards=(r.get('certificate')or{}).get('moving_sprite_evidence',[])
  if event and self.last['action']==6 and obs['state']=='NOT_FINISHED'and level==self.previous['levels_completed']and 7 in obs['available_actions']and not self.disabled and self.attempts.get(level,0)<12 and hazards and old['palette']==now['palette']and now['mass']<old['mass']:
   proof=dict(source=digest(event),level=level,click=copy.deepcopy(self.last['data']),before=old,after=now,expected_board=board_digest(self.previous),hypothesis='lost_composition_mass_after_click_near_observed_moving_sprites')
   self.failures.append(proof);self.pending=copy.deepcopy(proof);self.attempts[level]=self.attempts.get(level,0)+1
   r=dict(done=False,action=7,data={},certificate=dict(kind='waypoint_failure_recovery',context=digest(obs),failure=copy.deepcopy(proof),retained_failures=copy.deepcopy(self.failures),rollback_outcomes=copy.deepcopy(self.rollbacks),moving_sprite_evidence=copy.deepcopy(hazards),hypothesis='secondary_action_may_restore_the_failed_click_state'),advisor='waypoint_failure_recovery',diagnostics=dict(reason='test_rollback_after_observed_loss',attempts=self.attempts[level]))
   self.prefix.last=copy.deepcopy(r);self.prefix.prior.prior.last=copy.deepcopy(r)
  self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r);return r
