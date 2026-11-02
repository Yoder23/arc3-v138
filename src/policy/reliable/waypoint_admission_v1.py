"""One-time visual admission for waypoint motion and recursive block composition."""
from waypoint_action_learner_v2 import scene
from waypoint_recursive_inquiry_v15 import Agent as Waypoint

def route(raw):
 assert set(raw)=={'frame','state','available_actions','levels_completed'}
 if set(raw['available_actions'])=={6,7}:
  actors,points,goals,color=scene(raw)
  if len(actors)==1 and len(goals)==1 and len(points)>=4:return 'waypoint'
 return 'parent'
class Controller:
 def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
 def respond(self,raw):
  if not self.checked:
   self.checked=True;self.route=route(raw)
   if self.route=='waypoint':self.expert=Waypoint()
  return self.parent.respond(raw) if self.route=='parent' else self.expert.respond(raw)
