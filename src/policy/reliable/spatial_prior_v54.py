"""Retained pose hypotheses alongside the qualified existing skill collection."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'reliable'))
from adaptive_student import Agent as Prior
from retained_pose_learner_v2 import eligible
from snapshot_marker_pose import Learner
from visual_transform_learner import public
from panel_chain_hypotheses import candidates as dictionary_candidates
from editable_word_programs import layouts
from observed_composed_interface import recognized as composed_interface
from composite_connector_learner_v6 import objects,hypotheses
from guards import resource_limits,deny_external_state

class Agent:
    def __init__(self,arm='selective'):
        assert arm=='selective';self.prior=Prior(arm);self.learner=Learner();self.spatial=None;self.last=None;self.last_data={};self.steps=0
    def respond(self,raw):
        obs=public(raw)
        if self.spatial is None:
            self.spatial=False
            if obs['state']=='NOT_FINISHED' and eligible(obs):
                legal=set(obs['available_actions']);scene=objects(obs['frame'])
                dictionary=(legal<=set(range(1,6)) and (bool(dictionary_candidates(obs)['proposals']) or any(p['queries'] for p in layouts(obs)))) or composed_interface(obs)
                connector={1,2,3,4,5}<=legal and any(hypotheses(o,scene) for o in scene)
                self.spatial=not dictionary and not connector
        if not self.spatial:return self.prior.respond(obs)
        self.learner.observe(obs,self.last,self.last_data);c=self.learner.propose(obs)
        if c:self.learner.commit(c);action=c['action']
        else:action=self.learner.choose(obs)
        done=action is None;action=0 if done else action;self.last=action;self.last_data=c.get('data',{}) if c else {};self.steps+=int(not done)
        return dict(done=done,action=action,data=self.last_data,advisor='retained_pose',certificate=c,
            diagnostics=dict(spatial_actions=self.steps,actual_model_calls=0,retained_references=len(self.learner.references),
                actual_transition_rows=len(self.learner.rows),executed_failed_goals=len(self.learner.failed)))
def make_agent(arm):return Agent(arm)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=['selective'],required=True);args=ap.parse_args()
    job=resource_limits(cpu_seconds=600,memory_bytes=2*1024**3);agent=Agent(args.arm);sys.addaudithook(deny_external_state)
    print(json.dumps(dict(ready=True,arm=args.arm)),flush=True)
    for line in sys.stdin:print(json.dumps(agent.respond(json.loads(line)),separators=(',',':')),flush=True)
if __name__=='__main__':main()
