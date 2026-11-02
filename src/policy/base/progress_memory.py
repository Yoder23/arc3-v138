"""Bounded associative memory for observed click progress, never supplied goal labels."""
from collections import OrderedDict,Counter
import numpy as np
from click_objects import describe_scene,descriptor as object_descriptor
class ProgressMemory:
 def __init__(self,limit=32):
  self.limit=limit;self.evidence=OrderedDict();self.pending=None;self.events=set()
  self.last_biases={};self.successes=0;self.failures=0;self.queries=0;self.matches=0;self.selected=0
 @staticmethod
 def descriptor(frame,action,scene=None):
  return object_descriptor(frame,action,scene)
 def observe(self,obs):
  self.last_biases={}
  if self.pending is None:return
  event,level,feature=self.pending;self.pending=None
  if event in self.events:return
  progress=obs['levels_completed']>level or obs['state']=='WIN'
  failed=obs['state']=='GAME_OVER'
  if not(progress or failed):return
  self.events.add(event)
  # At most one outcome per actual action, even if observe is called twice.
  wins,losses=self.evidence.get(feature,(0,0))
  wins+=bool(progress);losses+=bool(failed and not progress)
  self.successes+=bool(progress);self.failures+=bool(failed and not progress)
  self.evidence[feature]=(wins,losses);self.evidence.move_to_end(feature)
  while len(self.evidence)>self.limit:self.evidence.popitem(last=False)
  # Recent event IDs are accounting only, never prediction features.
  if len(self.events)>4096:self.events=set(sorted(self.events)[-2048:])
 def remember(self,obs,action,event):
  feature=self.descriptor(obs['frame'],action)
  self.pending=None if feature is None else (event,obs['levels_completed'],feature)
 def biases(self,frame,actions):
  if not any(w>l for w,l in self.evidence.values()):return {}
  rows=[];valid=[];scene=describe_scene(frame)
  for action in actions:
   if action[0]!=6:continue
   self.queries+=1;feature=self.descriptor(frame,action,scene)
   if feature is not None:rows.append(feature);valid.append(action)
  result={}
  if rows:
   distances=np.count_nonzero(np.asarray(rows)[:,None,:]!=np.asarray(list(self.evidence))[None,:,:],axis=2)
   # Fixed radius1 on15object-role features. This is a tentative
   # analogy, not a supplied goal or an invariant game rule.
   kernels=np.maximum(0.,(2.-distances)/2.)
   outcomes=np.asarray(list(self.evidence.values()),dtype=float)
   reward=np.max(kernels*outcomes[:,0],axis=1);terminal=np.max(kernels*outcomes[:,1],axis=1)
   for action,value in zip(valid,np.clip(reward-terminal,0.,2.)):
    if value>0:result[action]=float(value);self.matches+=1
  self.last_biases=result.copy()
  return result
 def diagnostics(self):
  return dict(click_progress_success_events=self.successes,click_progress_terminal_events=self.failures,
   click_progress_memories=len(self.evidence),click_progress_queries=self.queries,
   click_progress_matches=self.matches,click_progress_selected=self.selected)
