"""Retained multi-symbol tool planning with preserved expert ownership."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'reliable'))
from parent_v58 import Agent as Prior
from constructive_tool_handoff_v2 import Controller
from optimistic_correspondence_handoff_v1 import Controller as CyclicController
from decorated_lattice_learner_v2 import Learner as DecoratedLatticeLearner
from revisable_connector_learner_v2 import Learner as RevisableConnectorLearner
from guards import resource_limits,deny_external_state

class Agent:
    def __init__(self,arm='selective'):
        self.tool_controller=Controller(Prior(arm))
        self.prior.learner=DecoratedLatticeLearner()
        self.prior.prior.learner=RevisableConnectorLearner()
        self.cyclic_controller=CyclicController(self.tool_controller)
    @property
    def controller(self):return self.tool_controller.prior.controller
    @property
    def spatial(self):return self.tool_controller.prior.spatial
    @property
    def prior(self):return self.tool_controller.prior.prior
    def respond(self,raw):return self.cyclic_controller.respond(raw)

def make_agent(arm):return Agent(arm)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=['selective'],required=True);args=ap.parse_args()
    job=resource_limits(cpu_seconds=600,memory_bytes=2*1024**3);agent=Agent(args.arm);sys.addaudithook(deny_external_state)
    print(json.dumps(dict(ready=True,arm=args.arm)),flush=True)
    for line in sys.stdin:print(json.dumps(agent.respond(json.loads(line)),separators=(',',':')),flush=True)
if __name__=='__main__':main()
