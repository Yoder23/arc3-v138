"""Suspend a stalled reference heuristic while preserving causal and goal memory."""
import copy
from role_filtered_reference_graph import Learner as Base,distance
from retained_object_graph_v3 import Learner as Exploration
from retained_object_graph import groups
from visual_transform_learner import public

class Learner(Base):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.attention_references={};self.best_distances={};self.reference_stall=0;self.reference_paused=False

    def observe(self,raw,action=None,data=None):
        obs=public(raw);old=self.previous;selected=self.pending;paused=self.reference_paused
        super().observe(obs,action,data)
        if old and (obs['levels_completed']!=old['levels_completed'] or obs['state']=='WIN' or action==0 and not self.retain):
            self.attention_references={};self.best_distances={};self.reference_stall=0;self.reference_paused=False
            return
        if not old or old['state']!=obs['state'] or obs['state']!='NOT_FINISHED':return
        observed=groups(obs)
        if selected and selected.get('reference_hypothesis'):
            ref=selected['reference_hypothesis'];self.attention_references[ref['id']]=copy.deepcopy(ref)
            d=distance(observed.get(ref['feature'],()),ref['target_poses'])
            if d is not None:
                if ref['id'] not in self.best_distances or d<self.best_distances[ref['id']]:
                    self.best_distances[ref['id']]=d;self.reference_stall=0
                else:self.reference_stall+=1
                if self.reference_stall>=16:self.reference_paused=True
        elif paused:
            improved=False
            for identity,ref in self.attention_references.items():
                if identity in self.failed_references:continue
                d=distance(observed.get(ref['feature'],()),ref['target_poses'])
                if d is not None and d<self.best_distances.get(identity,d):
                    self.best_distances[identity]=d;improved=True
            if improved:self.reference_paused=False;self.reference_stall=0

    def propose(self,raw):
        if not self.reference_paused:return super().propose(raw)
        c=Exploration.propose(self,raw)
        if c:
            c['reference_attention_pause']=dict(stalled_steps=self.reference_stall,
                retained_reference_ids=sorted(self.attention_references))
            c['scope']='Observed-state exploration while the reference-distance heuristic is suspended after sixteen selected reference steps without a new observed best distance. Transitions and goal hypotheses are retained. Actual distance improvement may restore the heuristic; no reference is refuted by stagnation alone.'
        return c
