"""One-time legal-pixel admission for qualified reflection and peg/carrier learners."""
from reflection_learning_admission_v3 import route as reflected_route
from reflection_assignment_inquiry_v18 import Agent as Reflection
from rail_peg_inquiry_v2 import Agent as Peg
from peg_jump_inquiry_v2 import scene,pegs

def route(raw):
 r=reflected_route(raw)
 if r!='parent':return r
 if 6 in raw['available_actions']:
  s=scene(raw['frame'])
  if s and len(pegs(raw['frame'],s))>1:return'peg'
 return'parent'
class Controller:
 def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
 def respond(self,raw):
  if not self.checked:
   self.checked=True;self.route=route(raw)
   if self.route=='reflection':self.expert=Reflection()
   elif self.route=='peg':self.expert=Peg()
  return self.parent.respond(raw)if self.route=='parent'else self.expert.respond(raw)
