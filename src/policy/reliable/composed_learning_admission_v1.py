"""One initial legal-pixel decision admits the qualified composition learners."""
from matrix_admission_v1 import admissible as matrix_admissible
from matrix_skill_graph_v7 import Agent as Matrix
from nested_sequence_inquiry_v6 import Agent as Nested
from nested_sequence_model_v3 import scene,synthesize

def route(raw):
 assert set(raw)=={'frame','state','available_actions','levels_completed'}
 if matrix_admissible(raw):return 'matrix'
 if set(raw['available_actions'])=={5,6,7}:
  parsed=scene(raw)
  if parsed and synthesize(parsed):return 'nested'
 return 'parent'
class Controller:
 def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
 def respond(self,raw):
  if not self.checked:
   self.checked=True;self.route=route(raw)
   if self.route=='matrix':self.expert=Matrix()
   elif self.route=='nested':self.expert=Nested()
  return self.parent.respond(raw)if self.route=='parent'else self.expert.respond(raw)
