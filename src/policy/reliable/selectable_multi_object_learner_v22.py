"""Retain visible goal frames around occupied bodies and discover newly exposed goals."""
import copy
from collections import Counter
from selectable_multi_object_learner_v21 import Agent as Base
from selectable_rect_geometry_v1 import rings
class Agent(Base):
    def observe(self,raw):
        r=super().observe(raw)
        if not r:return r
        bg=Counter(raw['frame'][y][x] for y,x in ((0,0),(0,63),(63,0),(63,63))).most_common(1)[0][0]
        for g in rings(raw['frame']):
            if g['ink'] in (bg,self.palette,self.floor) or not any(tuple(g['box'][2:])==(o['box'][2]+2,o['box'][3]+2) for o in self.objects):continue
            occupied=next((o for o in self.objects if tuple(o['box'])==(g['box'][0]+1,g['box'][1]+1,g['box'][2]-2,g['box'][3]-2)),None)
            if not occupied and g['center']!=self.floor:continue
            if any(tuple(old['box'])==tuple(g['box']) and old['ink']==g['ink'] for old in self.goals):continue
            self.goals.append(dict(g,observed_at=self.t,occupied_body_at_observation=copy.deepcopy(occupied),hypothesis='visible_outer_frame_may_be_a_goal_even_when_currently_occupied'))
        return r
