"""Select qualified connector or chained-dictionary skills; preserve full v18 elsewhere."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'reliable'))
from dictionary_student import Agent as Prior
from composite_connector_learner_v6 import Learner,objects,hypotheses,public
from panel_chain_hypotheses import candidates as dictionary_candidates
from guards import resource_limits,deny_external_state
from observed_composed_interface import recognized as composed_interface

class Agent:
    def __init__(self,arm='selective'):
        assert arm=='selective'
        self.prior=Prior(arm);self.learner=Learner()
        self.connector=None;self.last=None;self.steps=0
    def respond(self,obs):
        obs=public(obs)
        if self.connector is None:
            scene=objects(obs['frame']);legal=set(obs['available_actions'])
            dictionary=(bool(legal) and legal<=set(range(1,6)) and bool(dictionary_candidates(obs)['proposals'])) or composed_interface(obs)
            self.connector=not dictionary and obs['state']=='NOT_FINISHED' and {1,2,3,4,5}<=legal and any(hypotheses(o,scene) for o in scene)
        if not self.connector:return self.prior.respond(obs)
        self.learner.observe(obs,self.last);cert=self.learner.propose(obs)
        if cert:self.learner.commit(cert);action=cert['action']
        else:action=self.learner.choose(obs)
        done=action is None;action=0 if done else action;self.last=action;self.steps+=int(not done)
        return dict(done=done,action=action,data={},advisor='composite_connector',certificate=cert,
            diagnostics=dict(connector_actions=self.steps,actual_model_calls=0,models=len(self.learner.models),
                             retained_action_evidence=len(self.learner.rows)))
def make_agent(arm):return Agent(arm)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=['selective'],required=True);args=ap.parse_args()
    job=resource_limits(cpu_seconds=600,memory_bytes=2*1024**3)
    agent=Agent(args.arm);sys.addaudithook(deny_external_state)
    print(json.dumps(dict(ready=True,arm=args.arm)),flush=True)
    for line in sys.stdin:print(json.dumps(agent.respond(json.loads(line)),separators=(',',':')),flush=True)
if __name__=='__main__':main()
