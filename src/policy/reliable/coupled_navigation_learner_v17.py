"""Expose independently checkable evidence for speculative joint plans without changing actions."""
import copy
from coupled_navigation_learner_v16 import Agent as Prior
from visual_transform_learner import digest
class Agent(Prior):
    def respond(self,obs):
        response=super().respond(obs)
        if self.joint:
            j=self.joint
            if 'plan_certificate' not in j:
                m=self.manipulation;effects,_=self.controls();object_effects={a:tuple(d[0]) for a,d in effects.items() if a in (1,2,3,4,7)};transferred=set(object_effects)
                for a,deltas in m['models'].items():
                    if len(deltas)==1:object_effects[a]=next(iter(deltas));transferred.discard(a)
                b=dict(root=j['root'],selection_source=j['selection_source'],signature=j['signature'],inactive=j['inactive'],marker_color=j['marker_color'],selected_color=j['selected_color'],shape=j['shape'],positions=m['actor_positions'],marker=m['origin'],floor=self.floor_counts.most_common(1)[0][0],floor_sources=copy.deepcopy(self.floor_sources),hazard_hypotheses=copy.deepcopy(list(self.hazards.values())),effects=effects,support=j['model_support'],object_observations=j['object_observations'],object_effects=object_effects,transferred_actions=sorted(transferred),steps=[copy.deepcopy(j['expected'])]+copy.deepcopy(j['pending']),planning_is_hypothesis=True)
                j['plan_certificate']=b;j['plan_id']=digest(b)
            c=dict(kind='joint_relocation_hypothesis',context=digest(obs),action=response['action'],data=copy.deepcopy(response['data']),plan_id=j['plan_id'],index=j['issued']-1)
            if j['issued']==1:c['plan']=copy.deepcopy(j['plan_certificate'])
            response['certificate']=c
        return response
