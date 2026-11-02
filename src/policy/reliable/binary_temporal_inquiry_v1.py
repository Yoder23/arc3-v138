"""Use retained failure animations to plan and verify safe execution segments."""
import copy
from binary_contrastive_inquiry_v1 import Agent as Prefix
from binary_contrastive_geometry_v1 import controls,next_click,execution_effects
from binary_temporal_field_v1 import field_model,plan_temporal
from graph_semantic_digest_v2 import semantic_digest

class Agent:
    def __init__(self,prior=None):
        self.prior=prior;self.active=True;self.prefix=Prefix(prior);self.own=False;self.t=0
        self.pending=None;self.outcomes=[];self.plan=None
    def respond(self,raw):
        if not self.own:
            result=self.prefix.respond(raw);self.t=self.prefix.t
            if not result['done']or raw['state']!='NOT_FINISHED' or not self.prefix.own:return result
            self.values=copy.deepcopy(self.prefix.values);self.background=self.prefix.background
            self.field=field_model(self.prefix.trials,self.values,self.background)
            if self.field is None:return result
            self.known_models=copy.deepcopy(self.prefix.known_models);self.evidence=copy.deepcopy(self.prefix.trials)
            self.origin=self.t;self.level=raw['levels_completed'];self.frozen_prefix=semantic_digest(self.prefix);self.own=True
        assert semantic_digest(self.prefix)==self.frozen_prefix
        if self.pending:
            outcome=dict(self.pending,after=copy.deepcopy(raw))
            pairs,cs,scene=controls(raw,self.values,self.background)
            actual=list(scene['actor']['box'][:2])if scene else None
            outcome['actual_position']=actual
            outcome['matched']=actual==list(self.pending['plan']['expected_position'])
            outcome['level_advanced']=raw['levels_completed']>self.level
            self.outcomes.append(outcome);self.pending=None;self.plan=None
            if not outcome['matched']and not outcome['level_advanced']:return self.stop('temporal_or_persistence_prediction_refuted')
        if raw['state']!='NOT_FINISHED'or raw['levels_completed']!=self.level:return self.stop('terminal_or_level_advanced')
        if len(self.outcomes)>=4 or self.t-self.origin>=80:return self.stop('bounded_temporal_submissions')
        if self.plan is None:
            self.plan=plan_temporal(raw,self.values,self.background,self.field,self.known_models,self.outcomes)
            if self.plan is None:return self.stop('no_source_supported_temporal_route')
            self.plan=dict(self.plan,chosen_at=self.t,chosen_observation=copy.deepcopy(raw))
        action=next_click(raw,self.values,self.background,self.plan['program'])
        if action is None:return self.stop('control_geometry_unavailable')
        cert=dict(kind='retained_binary_temporal_inquiry',source=self.t,origin=self.origin,
                  values=self.values,background=self.background,field=copy.deepcopy(self.field),
                  known_models=copy.deepcopy(self.known_models),evidence=copy.deepcopy(self.evidence),
                  outcomes=copy.deepcopy(self.outcomes),plan=copy.deepcopy(self.plan),
                  stage=action['stage'],literal=action['literal'],frozen_prefix_digest=self.frozen_prefix)
        if action['stage']=='submit':self.pending=dict(source=self.t,before=copy.deepcopy(raw),plan=copy.deepcopy(self.plan),data=action['data'])
        self.t+=1
        return dict(done=False,action=6,data=action['data'],certificate=cert)
    def stop(self,reason):
        assert semantic_digest(self.prefix)==self.frozen_prefix
        return dict(done=True,action=None,data={},certificate=dict(kind='retained_binary_temporal_terminal',
                    source=self.t,origin=self.origin,reason=reason,field=self.field,outcomes=self.outcomes,
                    frozen_prefix_digest=self.frozen_prefix,prefix_preserved=True))
