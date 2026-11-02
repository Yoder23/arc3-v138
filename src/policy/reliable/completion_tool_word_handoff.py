"""Admit a learned tool sequence after an actual editable-word intervention.

Established specialist routes retain ownership. A paused expert is preserved
intact together with the actual observation ending its last selected action.
"""
import copy
from completion_tool_word_learner import Learner
from visual_transform_learner import public


def unowned_legacy(prior):
    graph = getattr(prior, "controller", None)
    if graph is not None and getattr(graph, "active", False):
        return False
    return prior.spatial is False and prior.prior.nested is False and prior.prior.prior.connector is False and prior.prior.prior.prior.panel is False


class Controller:
    def __init__(self, prior, *, retain=True):
        self.prior = prior
        self.learner = Learner(retain=retain)
        self.active = False
        self.last = None
        self.data = {}
        self.handoff = None
        self.steps = 0

    def respond(self, raw):
        obs = public(raw)
        self.learner.observe(obs, self.last, self.data)
        candidate = self.learner.propose(obs) if self.active or unowned_legacy(self.prior) else None
        if not self.active and candidate and candidate.get("goal") and any(self.learner.edited.values()):
            self.active = True
            self.handoff = dict(observation=copy.deepcopy(obs), preceding_actual_action=self.last,
                preceding_actual_data=copy.deepcopy(self.data), certificate=copy.deepcopy(candidate),
                prior_resumption_rule="Paused intact. No automatic resumption or delivery of outcomes for unselected actions.")
        if not self.active:
            response = self.prior.respond(obs)
        else:
            if candidate:
                self.learner.commit(candidate)
            action = candidate["action"] if candidate else None
            data = candidate["data"] if candidate else {}
            self.steps += int(action is not None)
            response = dict(done=action is None, action=0 if action is None else action, data=data,
                advisor="retained_tool_word", certificate=candidate,
                diagnostics=dict(tool_word_actions=self.steps, actual_model_calls=0,
                    retained_goal_sources=len(self.learner.sources),
                    observed_pair_effects=sum(map(len, self.learner.models.values()))))
        self.last = response["action"]
        self.data = copy.deepcopy(response["data"])
        return response
