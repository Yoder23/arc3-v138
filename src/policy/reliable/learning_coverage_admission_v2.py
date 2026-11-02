"""One-time visual admission of the new coupled learner; otherwise preserve the V89 parent."""
from learning_coverage_admission_v1 import route as previous_route
from coupled_navigation_learner_v20 import Agent as Coupled
def route(raw):return 'coupled' if previous_route(raw)=='coupled' else 'parent'
class Controller:
    def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
    def respond(self,raw):
        if not self.checked:
            self.checked=True;self.route=route(raw)
            if self.route=='coupled':self.expert=Coupled()
        return self.parent.respond(raw) if self.route=='parent' else self.expert.respond(raw)
