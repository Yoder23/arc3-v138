"""After an observed interaction opens a goal route, execute that route immediately."""
import copy
from matrix_program_composition_v4 import Agent as Base
from matrix_intermediate_learner_v3 import reachable,path,inside
class Agent(Base):
 def finish(self,raw,outcome):
  if outcome=='input_completed' and self.effect_seen_level==raw['levels_completed'] and self.moving:
   parents,_=reachable(self,raw);routes=[(len(path(parents,p)),p,g,path(parents,p)) for p in parents for g in self.goals if inside(p[0],p[1],g['box']) and path(parents,p)]
   if routes:
    _,p,g,route=min(routes,key=lambda q:(q[0],q[1]));e=self.ranged;self.ranged_memory.append(dict(start=e['start'],end=self.t,landmark=e['landmark'],pose=e['pose'],direction=e['direction'],outcome=outcome,world_effect_unconfirmed=True));self.ranged=None
    return self.answer(raw,route[0],{},'transfer_input_effect_to_goal',dict(effect_goal_plan=dict(route=route,goal=copy.deepcopy(g),effect_source=self.observed_input_effects[-1]['source'],goal_is_hypothesis=True)))
  return super().finish(raw,outcome)
