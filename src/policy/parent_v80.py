"""One-time observable admission; preserve the complete parent while carrying."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'reliable'))
from parent_v78 import Agent as Parent
from carry_admission_v3 import Controller
from binary_lattice_learner_v2 import Learner
from guards import resource_limits,deny_external_state
class Agent:
    def __init__(self,arm='selective'):
        self.parent=Parent(arm);self.parent.prior.learner=Learner();self.carry=Controller(self.parent)
    def respond(self,raw):return self.carry.respond(raw)
def make_agent(arm):return Agent(arm)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',choices=['selective'],required=True);args=ap.parse_args()
    job=resource_limits(cpu_seconds=600,memory_bytes=2*1024**3);agent=Agent(args.arm);sys.addaudithook(deny_external_state)
    print(json.dumps(dict(ready=True,arm=args.arm)),flush=True)
    for line in sys.stdin:print(json.dumps(agent.respond(json.loads(line)),separators=(',',':')),flush=True)
if __name__=='__main__':main()
