"""Admit the retained connector learner using only initial legal visual structure."""
from connector_assembly_admission_v2 import route as connector_route
from connector_assembly_learner_v21 import Agent as Connector
def route(raw):
    assert set(raw)=={'frame','state','available_actions','levels_completed'}
    return 'connector' if connector_route(raw)=='connector' else 'parent'
class Controller:
    def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
    def respond(self,raw):
        if not self.checked:
            self.checked=True;self.route=route(raw)
            if self.route=='connector':self.expert=Connector()
        return self.parent.respond(raw) if self.route=='parent' else self.expert.respond(raw)
