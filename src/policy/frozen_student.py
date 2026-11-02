"""Only legal observation streams enter fixed policy arms."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'base'))
from retained_object_family_scientist import Scientist
from adapter import PublicAgent
from guarded import GuardedAdvisors
from guards import resource_limits,deny_external_state

class Agent:
    def __init__(self,arm):
        self.arm=arm;self.core=Scientist('causal')
        if arm=='eager':self.core=PublicAgent().core
        elif arm in ('guarded','retained','selective','relational','coordinated','combined'):self.core.causal=GuardedAdvisors(arm!='guarded',require_change=arm in ('selective','relational','coordinated','combined'),generalize=arm in ('relational','combined'),respect_navigation=arm in ('coordinated','combined'),navigator=self.core.navigator)
        else:assert arm=='causal'
        if arm=='selective':
            self.core.causal.primary.spatial_aliases=True
            self.core.causal.primary.generalize=True
            self.core.causal.primary.extended_states=True
            self.core.causal.primary.model_experiments=True
    def respond(self,obs):
        response=self.core.respond(obs)
        advice=self.core.causal
        response['advisor']=getattr(advice,'selected',None) if not response.get('done') else None
        response['certificate']=advice.primary.certificate if response['advisor']=='dependency' else None
        return response

def make_agent(arm):return Agent(arm)
def main():
    p=argparse.ArgumentParser();p.add_argument('--arm',choices=['causal','eager','guarded','retained','selective','relational','coordinated','combined'],required=True);args=p.parse_args()
    job=resource_limits(cpu_seconds=600,memory_bytes=2*1024**3);agent=make_agent(args.arm)
    sys.addaudithook(deny_external_state)
    print(json.dumps(dict(ready=True,arm=args.arm)),flush=True)
    for line in sys.stdin:print(json.dumps(agent.respond(json.loads(line)),separators=(',',':')),flush=True)
if __name__=='__main__':main()
