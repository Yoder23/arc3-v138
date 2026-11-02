"""Compose advisors at the frozen N6E actual-action hook."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'base'))
from arc3_student_n6 import Scientist
from causal_clicks import CausalClicks
from dependencies import DependencyClicks

class Advisors:
    def __init__(self):
        self.primary=DependencyClicks(shapes=True);self.fallback=CausalClicks()
        self.selected=None;self.primary_actions=0;self.fallback_actions=0;self.abstentions=0
    def observe(self,frame,last=None,progress=False,reset=False):
        self.selected=None
        self.primary.observe(frame,last,progress=progress,reset=reset)
        self.fallback.observe(frame,last,progress=progress,reset=reset)
    def choose(self,legal):
        action=self.primary.choose(legal)
        if action is not None:
            self.selected='dependency';self.primary_actions+=1;return action
        self.abstentions+=1;action=self.fallback.choose(legal)
        if action is not None:self.selected='causal';self.fallback_actions+=1
        return action
    def diagnostics(self):
        return {**self.fallback.diagnostics(),**self.primary.diagnostics(),
                'primary_advisor_actions':self.primary_actions,'fallback_advisor_actions':self.fallback_actions,
                'primary_advisor_abstentions':self.abstentions}

class PublicAgent:
    def __init__(self,arm='dependency',seed=47000001):
        assert arm=='dependency';self.core=Scientist('causal');self.core.causal=Advisors()
    def respond(self,obs):
        response=self.core.respond(obs);advisor=self.core.causal
        response['certificate']=advisor.primary.certificate if not response.get('done') and advisor.selected=='dependency' else None
        response['advisor']=advisor.selected if not response.get('done') else None
        return response
