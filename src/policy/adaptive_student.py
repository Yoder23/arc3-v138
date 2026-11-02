"""Select a demonstrated miniature-pattern skill, preserving the full prior policy."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'reliable'))
from connector_student import Agent as Prior
from nested_constraint_learner_v2 import Learner
from nested_pattern_hypotheses import candidates
from visual_transform_learner import public
from guards import resource_limits,deny_external_state
class Agent:
    def __init__(self,arm='selective'):
        assert arm=='selective';self.prior=Prior(arm);self.learner=Learner()
        self.nested=None;self.last=None;self.data={};self.steps=0
    def respond(self,raw):
        obs=public(raw)
        if self.nested is None:
            self.nested=obs['state']=='NOT_FINISHED' and 6 in obs['available_actions'] and bool(candidates(obs['frame']))
        if not self.nested:return self.prior.respond(obs)
        self.learner.observe(obs,self.last,self.data);cert=self.learner.propose(obs)
        if cert:self.learner.commit(cert);action,data=cert['action'],cert['data']
        else:action,data=self.learner.choose(obs)
        done=action is None;action=0 if done else action;self.last=action;self.data=data;self.steps+=int(not done)
        return dict(done=done,action=action,data=data,advisor='nested_pattern',certificate=cert,
            diagnostics=dict(nested_actions=self.steps,actual_model_calls=0,remembered_rules=len(self.learner.memory),
                actual_click_samples=len(self.learner.samples)))
def make_agent(arm):return Agent(arm)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=['selective'],required=True);args=ap.parse_args()
    job=resource_limits(cpu_seconds=600,memory_bytes=2*1024**3);agent=Agent(args.arm);sys.addaudithook(deny_external_state)
    print(json.dumps(dict(ready=True,arm=args.arm)),flush=True)
    for line in sys.stdin:print(json.dumps(agent.respond(json.loads(line)),separators=(',',':')),flush=True)
if __name__=='__main__':main()
