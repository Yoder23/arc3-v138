"""Use a learned navigation program, then bind the interaction program to the visible target."""
import copy
from matrix_program_alternatives_v5 import Agent as Base
class Agent(Base):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.context_program=None
 def respond(self,raw):
  self.context_program=None
  if self.ranged and self.ranged['phase'] in ('approach','clear'):
   target=self.ranged['landmark'];binding=next((b for b in self.program_bindings if b['reference']['ink']==target['ink']),None)
   if binding:
    chosen=binding['points'];self.programs=[chosen]+[p for p in self.programs if p!=chosen];self.context_program=dict(binding=copy.deepcopy(binding),landmark=copy.deepcopy(target),goal_is_hypothesis=True)
  return super().respond(raw)
 def answer(self,raw,*args,**kwargs):
  r=super().answer(raw,*args,**kwargs)
  if not r['done'] and self.context_program:r['certificate']['context_program']=copy.deepcopy(self.context_program);self.previous['certificate']=copy.deepcopy(r['certificate'])
  return r
