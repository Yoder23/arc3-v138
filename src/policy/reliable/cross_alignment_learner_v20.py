"""Retain the established learner and admit shared-color scene decomposition from pixels."""
from cross_alignment_learner_v3 import Agent as Prior
from cross_shared_goal_learner_v17 import Agent as Shared
from cross_shape_geometry_v2 import scene
from cross_shape_geometry_v1 import scene as prior_scene
class Agent:
    def __init__(self):self.prior=Prior();self.shared=None
    def respond(self,obs):
        if self.shared is None:
            objs,targets=scene(obs);colors=[o['color'] for o in objs.values()]
            if len(objs)>len(set(colors)) and len(objs)>=2 and bool(targets):
                self.prior.observe(obs,prior_scene(obs)[0]);self.shared=Shared(self.prior)
        return self.shared.respond(obs) if self.shared else self.prior.respond(obs)
