"""Observation-based visual-dictionary specialist with exact v18 delegation elsewhere."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'reliable'))
from v18_student import Agent as Legacy
from adaptive_dictionary_learner_v11 import Learner
from guards import resource_limits,deny_external_state
class Agent:
    def __init__(self,arm='selective'):
        assert arm=='selective';self.legacy=Legacy(arm);self.learner=Learner();self.panel=None;self.last_action=None;self.steps=0
    def respond(self,obs):
        if self.panel is None:
            self.learner.observe(obs,None);legal=set(obs['available_actions'])
            self.panel=obs['state']=='NOT_FINISHED' and bool(legal) and legal<=set(range(1,6)) and bool(self.learner.hypotheses or any(p['queries'] for p in self.learner.program.parsed) or any(p['queries'] for p in self.learner.composed.parsed))
        elif self.panel:self.learner.observe(obs,self.last_action)
        if not self.panel:return self.legacy.respond(obs)
        cert=self.learner.propose(obs)
        if cert:self.learner.commit(cert);action=cert['action']
        else:action=self.learner.choose(obs)
        done=action is None;action=0 if done else action;self.last_action=action;self.steps+=int(not done)
        return dict(done=done,action=action,data={},advisor='panel_chain',certificate=cert,diagnostics=dict(panel_actions=self.steps,actual_model_calls=0,remembered_hypotheses=len(self.learner.hypotheses),edit_samples=len(self.learner.edit_rows),selection_samples=len(self.learner.select_rows)))
def make_agent(arm):return Agent(arm)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=['selective'],required=True);args=ap.parse_args()
    job=resource_limits(cpu_seconds=600,memory_bytes=2*1024**3);agent=Agent(args.arm);sys.addaudithook(deny_external_state)
    print(json.dumps(dict(ready=True,arm=args.arm)),flush=True)
    for line in sys.stdin:print(json.dumps(agent.respond(json.loads(line)),separators=(',',':')),flush=True)
if __name__=='__main__':main()
