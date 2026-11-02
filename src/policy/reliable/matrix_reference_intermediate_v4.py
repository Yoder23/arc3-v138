"""Resume the goal after a real input changes another nearby observed object."""
import copy
from matrix_reference_intermediate_v3 import Agent as Base
from matrix_motion_learner_v6 import objects
from matrix_intermediate_learner_v3 import gap
class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.observed_input_effects=[];self.effect_seen_level=None
    def respond(self,raw):
        if self.level!=raw['levels_completed'] or raw['state']!='NOT_FINISHED' or self.previous and self.previous['action']==0:self.effect_seen_level=None
        return super().respond(raw)
    def reference_targets(self,raw):
        if self.effect_seen_level==raw['levels_completed']:return []
        return super().reference_targets(raw)
    def observe(self,raw):
        old=self.previous
        super().observe(raw)
        if not old or old['action']!=6 or not self.grid or old['raw']['levels_completed']!=raw['levels_completed'] or not old['certificate'].get('ranged_plan',{}).get('phase')=='program':return
        body=old['certificate'].get('moving')
        if not body:return
        for item in objects(old['raw']['frame'],[self.grid['box'],body['box']]):
            if item.get('parts') or gap(item['box'],body['box'])>32 or gap(item['box'],self.grid['box'])<=12:continue
            y,x,h,w=item['box'];changed=[(y+dy,x+dx,old['raw']['frame'][y+dy][x+dx],raw['frame'][y+dy][x+dx]) for dy,dx in item['shape'] if old['raw']['frame'][y+dy][x+dx]!=raw['frame'][y+dy][x+dx]]
            if changed:
                self.observed_input_effects.append(dict(source=old['source'],object=copy.deepcopy(item),changed=changed,hypothesis='observed_object_change_justifies_retrying_goal_route'))
                self.effect_seen_level=raw['levels_completed']
