"""Progress-scoped authority and tentative memory across matching visual restarts."""
import copy
from dependencies import DependencyClicks
from causal_clicks import CausalClicks

class ProgressClicks(DependencyClicks):
    def __init__(self,retain,require_change=False,generalize=False):
        self.retain=retain;self.require_change=require_change;self.bank={};self.layout_key=None;self.awaiting_start=True
        self.level_actions=0;self.level_probes=0;self.level_age=0
        self.navigation_probe_vetoes=0;self.restores=0;self.restored_observations=0;self.restored_state_experiences=0;self.novelty_abstentions=0;self.budget_abstentions=0
        super().__init__(shapes=True,generalize=generalize)
    def observe(self,frame,last=None,progress=False,reset=False):
        if progress:
            self.bank={};self.layout_key=None;self.awaiting_start=True
            self.level_actions=0;self.level_probes=0;self.level_age=0
        elif reset and self.layout_key is not None:
            if self.retain and (not self.require_change or any(e.changed for e in self.models.values())):
                self.bank[self.layout_key]=(copy.deepcopy(self.models),set(self.rejected_goals),self.state_visits.copy(),self.action_visits.copy())
                while len(self.bank)>8:del self.bank[next(iter(self.bank))]
            self.layout_key=None;self.awaiting_start=True
        super().observe(frame,last,progress,reset)
        self.level_age+=1
        if not reset and self.last is not None and self.awaiting_start:
            self.layout_key=(tuple(self.slots),self.last);self.awaiting_start=False
            if self.retain and self.layout_key in self.bank:
                self.models,self.rejected_goals,past_states,past_actions=copy.deepcopy(self.bank[self.layout_key])
                self.state_visits.update(past_states);self.action_visits.update(past_actions)
                self.restored_state_experiences+=sum(past_states.values())
                self.restores+=1;self.restored_observations+=sum(len(e.history) for e in self.models.values())
    def choose(self,legal,allow_probe=True):
        if self.level_age<40:return None
        if self.level_actions>=224:
            self.budget_abstentions+=1;return None
        # The inherited proposer mutates its pending route and counters.
        # A declined probe is explicitly rolled back before any real action.
        pending=list(self.pending)
        action=super().choose(legal)
        if action is None:return None
        probe=self.certificate['kind']=='probe'
        if probe:
            effect=self.models.get(action)
            familiar=effect is not None and any(old==self.last for old,new in effect.history)
            if familiar or self.level_probes>=64 or not allow_probe:
                self.probes-=1;self.delegated-=1;self.action_visits[action]-=1
                self.pending=pending;self.certificate=None
                if familiar:self.novelty_abstentions+=1
                elif self.level_probes>=64:self.budget_abstentions+=1
                else:self.navigation_probe_vetoes+=1
                return None
            self.level_probes+=1
        self.level_actions+=1
        return action
    def diagnostics(self):
        return {**super().diagnostics(),'progress_primary_actions':self.level_actions,
          'progress_primary_probes':self.level_probes,'progress_age':self.level_age,
          'restart_state_experiences_restored':self.restored_state_experiences,'restart_memories':len(self.bank),'restart_restores':self.restores,
          'restart_observations_restored':self.restored_observations,
          'novelty_abstentions':self.novelty_abstentions,'budget_abstentions':self.budget_abstentions}

class GuardedAdvisors:
    def __init__(self,retain,require_change=False,generalize=False,respect_navigation=False,navigator=None):
        self.primary=ProgressClicks(retain,require_change,generalize);self.fallback=CausalClicks()
        self.selected=None;self.primary_actions=0;self.fallback_actions=0;self.abstentions=0
        self.navigator=navigator;self.respect_navigation=respect_navigation;self.previous_actor=None;self.motion_age=100000;self.guard_active=False
    def observe(self,frame,last=None,progress=False,reset=False):
        self.selected=None;self.guard_active=False
        nav=self.navigator;actor=None
        if nav is not None and nav.position is not None:
            actor=(nav.identity,nav.position['y'],nav.position['x'])
        if progress or reset:
            self.motion_age=100000;self.previous_actor=None
        else:
            self.motion_age+=1
            if actor is not None and self.previous_actor is not None and actor[0]==self.previous_actor[0] and actor[1:]!=self.previous_actor[1:] and last is not None and last[0] in (1,2,3,4,5,7):
                self.motion_age=0
        self.previous_actor=None if reset else actor
        self.primary.observe(frame,last,progress,reset)
        self.fallback.observe(frame,last,progress,reset)
    def choose(self,legal):
        # Only call choose on an advisor when its returned action will execute.
        action=self.fallback.choose(legal)
        if action is not None:
            self.selected='causal';self.fallback_actions+=1;return action
        nav=self.navigator
        supported=nav is not None and nav.position is not None and sum(nav.effect(nav.identity,a) is not None for a in legal if a in (1,2,3,4,5,7))>=2
        self.guard_active=bool(self.respect_navigation and 6 in legal and supported and self.motion_age<=8 and not any(e.changed for e in self.primary.models.values()))
        action=self.primary.choose(legal,allow_probe=not self.guard_active)
        if action is not None:
            self.selected='dependency';self.primary_actions+=1;return action
        self.abstentions+=1;return None
    def diagnostics(self):
        extra={'navigation_probe_vetoes':self.primary.navigation_probe_vetoes,'recent_translation_age':self.motion_age,'navigation_guard_active':self.guard_active} if self.respect_navigation else {}
        return {**extra,**self.fallback.diagnostics(),**self.primary.diagnostics(),
          'primary_advisor_actions':self.primary_actions,'fallback_advisor_actions':self.fallback_actions,
          'primary_advisor_abstentions':self.abstentions}
