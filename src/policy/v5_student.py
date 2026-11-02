"""One fixed public-observation hybrid; never receives a game identifier."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'reliable'))
from resumable_legacy_learner import ReliableLearner
from frozen_student import Agent as FrozenAgent
from guards import resource_limits,deny_external_state

class Agent:
    def __init__(self,arm):
        assert arm=='selective'
        self.fallback=FrozenAgent(arm);self.core=self.fallback.core
        self.used=0;self.started=False;self.fallback_only=False;self.stream=None;self.learner=None
        self.prior=None;self.last_result=None
    @staticmethod
    def eligible(obs):
        return obs['state']=='NOT_FINISHED' and bool(obs['available_actions']) and set(obs['available_actions'])<=set((1,2,3,4))
    def respond(self,obs):
        if not self.started:
            self.started=True;self.fallback_only=not self.eligible(obs)
        proposal=None
        if self.stream is not None:
            try:proposal=self.stream.send(obs)
            except StopIteration as finished:
                self.last_result=finished.value;self.prior=finished.value['learned_knowledge'];self.stream=None
        if obs['state']=='WIN':return dict(done=True,action=0,data={},advisor=None,certificate=None)
        if self.fallback_only:return self.fallback.respond(obs)
        if proposal is None and self.used<96 and self.eligible(obs):
            self.learner=ReliableLearner(self.prior)
            self.stream=self.learner.interact(obs,max_actions=96-self.used)
            proposal=next(self.stream)
        if proposal is not None and self.used<96 and proposal['action'] in (1,2,3,4) and proposal['action'] in obs['available_actions']:
            self.used+=1
            return dict(done=False,action=proposal['action'],data={},advisor='reliable',certificate=None,
                diagnostics=dict(reliable_actions_proposed=self.used,actor=self.learner.actor,
                    collision_hypotheses=len(self.learner.blocking_labels),control_authority=self.learner.control_authority,
                    suspended_global_actions=sorted(self.learner.memory.suspended),actual_model_calls=0))
        if self.stream is not None:self.stream.close();self.stream=None
        self.fallback_only=True
        return self.fallback.respond(obs)
def make_agent(arm):return Agent(arm)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--arm',choices=['selective'],required=True);args=parser.parse_args()
    job=resource_limits(cpu_seconds=600,memory_bytes=2*1024**3);agent=make_agent(args.arm)
    sys.addaudithook(deny_external_state)
    print(json.dumps(dict(ready=True,arm=args.arm)),flush=True)
    for line in sys.stdin:print(json.dumps(agent.respond(json.loads(line)),separators=(',',':')),flush=True)
if __name__=='__main__':main()
