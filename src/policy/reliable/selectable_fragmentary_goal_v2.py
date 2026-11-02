"""Invalidate a cached approach when its target pixels change, then observe and replan."""
import copy
from selectable_fragmentary_goal_v1 import Agent as Base
class Agent(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.target_invalidations=[]
    def respond(self,raw):
        state=self.passive_probe_state
        if state and not state.get('contact') and raw['state']=='NOT_FINISHED' and self.level==raw['levels_completed']:
            q=state['target'];y,x,h,w=q['box'];changes=[(y+a,x+b,q['ink'],raw['frame'][y+a][x+b]) for a,b in q['shape'] if raw['frame'][y+a][x+b]!=q['ink']]
            if changes:
                self.target_invalidations.append(dict(source=self.previous['source'],observed_at=self.t,target=copy.deepcopy(q),changes=changes,causality_is_hypothesis=True,outcome='cached_target_refuted_by_current_pixels'));self.passive_probe_state=None
        r=super().respond(raw)
        if r['done'] and self.target_invalidations:r['target_invalidations']=copy.deepcopy(self.target_invalidations)
        return r
    def answer(self,*args,**kwargs):
        r=super().answer(*args,**kwargs)
        if not r['done'] and self.target_invalidations:r['certificate']['target_invalidations']=copy.deepcopy(self.target_invalidations)
        return r
