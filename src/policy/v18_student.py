"""Fixed interface rule and fixed advisor handoff; no game identity input."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent/'reliable'))
from v5_student import Agent as Legacy
from advisor_retry_session import AdvisorRetrySession
from guards import resource_limits, deny_external_state

RETAIN = True

class Agent:
    def __init__(self, arm):
        assert arm == 'selective'
        self.legacy = Legacy(arm)
        self.core = self.legacy.core
        self.started = False
        self.retry_mode = False
        self.session = None

    def respond(self, obs):
        if not self.started:
            self.started = True
            actions = set(obs['available_actions'])
            self.retry_mode = obs['state'] == 'NOT_FINISHED' and 2 <= len(actions) and actions <= set(range(1, 6))
            if self.retry_mode:
                self.session = AdvisorRetrySession(self.legacy, retain_advisor=RETAIN)
        return self.session.respond(obs) if self.retry_mode else self.legacy.respond(obs)

def make_agent(arm):
    return Agent(arm)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--arm', choices=['selective'], required=True)
    args = parser.parse_args()
    job = resource_limits(cpu_seconds=600, memory_bytes=2*1024**3)
    agent = make_agent(args.arm)
    sys.addaudithook(deny_external_state)
    print(json.dumps(dict(ready=True, arm=args.arm)), flush=True)
    for line in sys.stdin:
        print(json.dumps(agent.respond(json.loads(line)), separators=(',', ':')), flush=True)

if __name__ == '__main__':
    main()
