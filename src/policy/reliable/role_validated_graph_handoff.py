"""Hand an unsupported legacy route to an evidence-backed reference experiment.

The old expert is paused intact. Its next actual observation is saved at handoff;
it never receives an outcome for an action it did not select. This controller
keeps graph ownership for the rest of the game, including resets and new levels.
"""
import copy
from role_validated_reflective_graph import Learner
from visual_transform_learner import public

def legacy_only(prior):
    return prior.spatial is False and prior.prior.nested is False and prior.prior.prior.connector is False and prior.prior.prior.prior.panel is False

class Controller:
    def __init__(self,prior):
        self.prior=prior;self.graph=Learner();self.active=False
        self.last=None;self.data={};self.steps=0;self.handoff=None

    def respond(self,raw):
        obs=public(raw);self.graph.observe(obs,self.last,self.data)
        candidate=self.graph.propose(obs) if self.active or legacy_only(self.prior) else None
        if not self.active and candidate and candidate.get('reference_hypothesis'):
            self.active=True
            self.handoff=dict(observation=copy.deepcopy(obs),preceding_actual_action=self.last,
                preceding_actual_data=copy.deepcopy(self.data),certificate=copy.deepcopy(candidate),
                prior_resumption_rule='Consume this saved actual observation before considering any later observation. No automatic resumption in this controller.')
        if not self.active:
            response=self.prior.respond(obs)
        else:
            if candidate:self.graph.commit(candidate);action=candidate['action'];data=candidate.get('data',{})
            else:action=self.graph.choose(obs);data={}
            done=action is None
            response=dict(done=done,action=0 if done else action,data=data,advisor='retained_object_graph',certificate=candidate,
                diagnostics=dict(graph_actions=self.steps+int(not done),actual_model_calls=0,
                    retained_observed_transitions=len(self.graph.history),remembered_references=len(self.graph.references)))
            self.steps+=int(not done)
        self.last=response['action'];self.data=copy.deepcopy(response['data'])
        return response
