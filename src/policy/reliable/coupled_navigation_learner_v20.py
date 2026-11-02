"""Resolve ambiguous actor candidates by controlled motion rather than color priority."""
import copy
from coupled_navigation_learner_v19 import Agent as Prior
from coupled_navigation_core_v10 import actors
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest

def candidates(obs):
    groups={}
    for q in parts(obs['frame']):
        if q['y']>0 and q['h']==q['w'] and q['area']==q['h']*q['w'] and 2<=q['h']<=8:groups.setdefault((q['color'],q['h']),[]).append((q['y'],q['x']))
    return {k:tuple(sorted(v,key=lambda p:(p[1],p[0]))) for k,v in groups.items() if len(v)==2}
class Agent(Prior):
    def __init__(self):super().__init__();self.actor_identity_evidence={};self.actor_identity_decisions=[]
    def respond(self,obs):
        if self.signature is None and self.previous and self.level==obs['levels_completed'] and self.last in (1,2,3,4,7) and self.previous['state']=='NOT_FINISHED' and obs['state']=='NOT_FINISHED':
            before,after=candidates(self.previous),candidates(obs);moving=[k for k in before if k in after and before[k]!=after[k]];row=dict(before=self.previous,action=self.last,data=self.last_data,after=obs);source=digest(row)
            if len(moving)==1:
                key=moving[0];evidence=self.actor_identity_evidence.setdefault((self.level,key),{});evidence[source]=dict(source=source,action=self.last,before=before[key],after=after[key])
                if len(evidence)>=2 and len({q['action'] for q in evidence.values()})>=2:
                    self.signature=key;self.previous_pos=before[key];initial=next((q['before'] for q in self.history.values() if q['before']['levels_completed']==self.level),self.previous);_,spawn=actors(initial['frame'],key);self.spawn_pos=spawn or before[key];self.spawn_source=digest(initial);self.actor_identity_decisions.append(dict(level=self.level,signature=key,support=copy.deepcopy(list(evidence.values())),interpretation='uniquely_moving_equal_square_pair'))
        response=super().respond(obs);response['diagnostics']['temporal_actor_identities']=len(self.actor_identity_decisions);return response
