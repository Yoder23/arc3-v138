"""Retain conditional object-control evidence and reuse it on later matching selections."""
import copy
from coupled_navigation_learner_v17 import Agent as Prior
from coupled_navigation_manipulation_v2 import recolor_mode
from visual_transform_learner import digest
from coupled_navigation_core_v10 import landmarks
class Agent(Prior):
    def __init__(self):
        super().__init__();self.conditional_knowledge={};self.control_transfers=[];self.control_refutations=[];self.selection_hypotheses=set()
    def respond(self,obs):
        if self.manipulation is None and self.joint is None:
            m=recolor_mode(self,obs)
            if m:
                key=digest(dict(level=m['level'],signature=m['signature'],shape=m['shape'],inactive=m['inactive'],marker_color=m['marker_color'],selected_color=m['selected_color'],actor_controls=self.controls()[0]));m['knowledge_key']=key
                stored=self.conditional_knowledge.get(key)
                if stored:
                    m['observations']=copy.deepcopy(list(stored.values()))
                    for record in stored.values():
                        delta=tuple(record['delta'])
                        if delta!=(0,0):m['models'].setdefault(record['action'],{}).setdefault(delta,[]).append(record['source'])
                    self.control_transfers.append(dict(source=m['source'],context=key,retained_sources=list(stored)))
                self.manipulation=m
        previous=self.manipulation;response=super().respond(obs)
        if previous and 'knowledge_key' in previous:
            key=previous['knowledge_key'];stored=self.conditional_knowledge.setdefault(key,{})
            for record in previous['observations']:
                if record['source'] in stored or tuple(record['delta'])==(0,0):continue
                prior={tuple(q['delta']) for q in stored.values() if q['action']==record['action']}
                if prior and tuple(record['delta']) not in prior:self.control_refutations.append(dict(source=record['source'],context=key,action=record['action'],rejected=sorted(prior),observed=record['delta']))
                stored[record['source']]=copy.deepcopy(record)
        if response['diagnostics']['reason']=='identify_coupled_controls' and not self.manipulation and not self.joint and self.floor_counts and len(self.controls()[0])>=4 and sum(self.trials.values())>=15 and 6 in obs['available_actions']:
            candidates=landmarks(obs,self.floor_counts.most_common(1)[0][0],self.signature[1],self.hazards,self.signature[0])
            for q in candidates:
                key=(self.level,q['color'],tuple(map(tuple,q['pixels'])),tuple(sorted(self.hazards)))
                if key in self.selection_hypotheses:continue
                self.selection_hypotheses.add(key);y,x=q['pixels'][0];self.last=6;self.last_data=dict(x=x,y=y);self.predicted=None;response.update(action=6,data=copy.deepcopy(self.last_data),certificate=None);response['diagnostics']['reason']='test_selectable_obstacle_without_actor_route';break
        response['diagnostics'].update(conditional_skills=len(self.conditional_knowledge),control_transfers=len(self.control_transfers),control_refutations=len(self.control_refutations));return response
