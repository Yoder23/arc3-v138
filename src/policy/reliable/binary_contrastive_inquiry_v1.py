"""Retain the old learner, revise failed commands through controlled contrasts."""
import copy
from binary_rolling_program_v1 import Agent as Prefix
from graph_semantic_digest_v2 import semantic_digest
from binary_contrastive_geometry_v1 import failed_moves, select_program, next_click, execution_effects

class Agent:
    def __init__(self, prior=None):
        self.prior=prior;self.active=True;self.prefix=Prefix(prior);self.t=0
        self.own=False;self.prefix_trials=[];self.prefix_pending=None
        self.trials=[];self.pending=None;self.plan=None;self.values=None;self.background=None

    def respond(self,raw):
        if self.prefix_pending is not None:
            self.prefix_trials.append(dict(self.prefix_pending,after=copy.deepcopy(raw)))
            self.prefix_pending=None
        if not self.own:
            result=self.prefix.respond(raw);self.t=self.prefix.t
            cert=result.get('certificate')or{}
            if not result['done']:
                if cert.get('tag')=='test_observed_column_program':
                    self.prefix_pending=dict(source=self.t-1,before=copy.deepcopy(raw),program=copy.deepcopy(cert['plan']),scene=copy.deepcopy(cert['scene']))
                return result
            if raw['state']!='NOT_FINISHED' or not self.prefix.models:
                return result
            self.values=copy.deepcopy(self.prefix.bootstrap.values);self.background=self.prefix.main_background
            self.known_models=[]
            for archive in self.prefix.model_archive:
                self.known_models.extend(dict(copy.deepcopy(m),retained_level=archive['level']) for m in archive['models'])
            self.known_models.extend(dict(copy.deepcopy(m),retained_level=self.prefix.learner_level) for m in self.prefix.models.values())
            self.failures=[]
            for trial in self.prefix_trials:
                if trial['before']['levels_completed']==raw['levels_completed']==trial['after']['levels_completed']:
                    self.failures.extend(failed_moves(trial,self.values,self.background))
            if not self.failures:return result
            self.origin=self.t;self.initial_level=raw['levels_completed'];self.frozen_prefix=semantic_digest(self.prefix);self.own=True
        assert semantic_digest(self.prefix)==self.frozen_prefix
        if self.pending:
            trial=dict(self.pending,after=copy.deepcopy(raw))
            trial['effects']=execution_effects(trial,self.values,self.background)
            self.trials.append(trial);self.pending=None;self.plan=None
        if raw['state']!='NOT_FINISHED' or raw['levels_completed']!=self.initial_level:
            return self.stop('level_changed_or_terminal')
        if self.t-self.origin>=120:return self.stop('bounded_action_limit')
        if self.plan is None:
            self.plan=select_program(raw,self.values,self.background,self.known_models,self.failures,self.trials)
            if self.plan is None:return self.stop('no_untried_contrast_or_new_effect_route')
            self.plan=dict(self.plan,chosen_at=self.t,chosen_observation=copy.deepcopy(raw))
        action=next_click(raw,self.values,self.background,self.plan['program'])
        if action is None:return self.stop('control_geometry_unavailable')
        cert=dict(kind='retained_binary_contrastive_inquiry',source=self.t,origin=self.origin,
                  values=self.values,background=self.background,known_models=copy.deepcopy(self.known_models),
                  failures=copy.deepcopy(self.failures),prefix_trials=copy.deepcopy(self.prefix_trials),
                  trials=copy.deepcopy(self.trials),plan=copy.deepcopy(self.plan),stage=action['stage'],
                  literal=action['literal'],frozen_prefix_digest=self.frozen_prefix,
                  generalization_is_hypothesis=True)
        if action['stage']=='submit':
            self.pending=dict(self.plan,source=self.t,before=copy.deepcopy(raw),data=action['data'])
        self.t+=1
        return dict(done=False,action=6,data=action['data'],certificate=cert)

    def stop(self,reason):
        assert semantic_digest(self.prefix)==self.frozen_prefix
        return dict(done=True,action=None,data={},certificate=dict(kind='retained_binary_contrastive_terminal',
                    source=self.t,origin=self.origin,reason=reason,failures=self.failures,trials=self.trials,
                    frozen_prefix_digest=self.frozen_prefix,prefix_preserved=True))
