"""Visible shape/action admission; V117 handles every other observation."""
from animated_switch_navigation_v5 import Agent as Expert, scene


def route(raw):
    return 'animated_switch' if set(raw['available_actions']) == {1,2,3,4,5} and scene(raw['frame']) else 'parent'


class Controller:
    def __init__(self,parent):
        self.parent=parent;self.route=None;self.expert=None
    def respond(self,raw):
        if self.route is None:
            self.route=route(raw)
            if self.route=='animated_switch':self.expert=Expert()
        return self.expert.respond(raw) if self.expert else self.parent.respond(raw)
