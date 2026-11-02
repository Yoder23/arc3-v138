"""Preserve preferred grasp axes and check delivery feasibility before commitment."""
import copy
from carry_interaction_learner_v4 import Controller as Base
from carry_interaction_learner_v2 import plus,minus

class Controller(Base):
    def delivery_possible(self,v,target,action,slots):
        offset=tuple(self.motions[action]['delta'])
        hypothetical=copy.deepcopy(v)
        hypothetical['body']['box']=minus(target,offset)+tuple(v['body']['box'][2:])
        return any(self.route(hypothetical,minus(slot,offset),offset) is not None
                   for slot in sorted(slots-self.positions(v)))

    def respond(self,raw):
        level=raw['levels_completed']
        if self.level is not None and level!=self.level:
            self.episode_bank.append(dict(level=self.level,goal=copy.deepcopy(self.goal),motions=copy.deepcopy(self.motions),
                signature=self.signature,attachment=copy.deepcopy(self.attachment),boundary_observed_at=self.t))
            self.previous=None;self.signature=None;self.phase=None;self.goal=None;self.motions={};self.blocked=set()
            self.held=None;self.attachment=None;self.mode=None;self.target=None;self.trials.clear();self.no_goal_steps=0
        self.level=level
        assert set(raw)<= {'frame','state','available_actions','levels_completed'}
        v=self.view(raw);self.record(raw,v)
        if raw['state']=='WIN':return dict(done=True,action=None,data={})
        if raw['state']=='GAME_OVER':
            if not self.retain:
                self.goal=None;self.motions={};self.blocked=set();self.attachment=None;self.trials.clear()
            self.held=None;self.mode=None;self.target=None
            return self.answer(raw,v,0,'reset_after_failure')
        if v is None:
            return self.prior.respond(raw) if self.prior and not self.active else dict(done=True,action=None,data={})
        self.active=True;allowed=raw['available_actions'];at=tuple(v['body']['box'][:2])
        if len(self.motions)<4:
            a=min(allowed,key=lambda a:(a in self.motions,self.trials[a],a))
            return self.answer(raw,v,a,'motion_inquiry')
        aux=[a for a in allowed if a not in self.motions]
        if not aux:return dict(done=True,action=None,data={})
        if self.goal is None:
            self.no_goal_steps+=1
            if self.no_goal_steps>12:return dict(done=True,action=None,data={})
            return self.answer(raw,v,min(allowed,key=lambda a:(self.trials[a],a)),'goal_unknown_probe')
        if self.mode in ('verify_pick','verify_drop'):
            offset=self.held
            if offset is None and self.target is not None:offset=minus(self.target,at)
            choices=[]
            for a,m in self.motions.items():
                route=self.route(v,plus(at,m['delta']),self.held)
                if route and len(route)==1:
                    away=0 if offset and sum(x*y for x,y in zip(offset,m['delta']))<0 else 1
                    choices.append((away,a))
            if choices:return self.answer(raw,v,min(choices)[1],self.mode)
            self.mode=None
        slots=self.slots();cargo=self.positions(v)
        if self.held is not None:
            held=plus(at,self.held);loose=cargo-{held};choices=[]
            if held in slots:return self.answer(raw,v,aux[0],'release')
            for slot in sorted(slots-loose):
                route=self.route(v,minus(slot,self.held),self.held)
                if route is not None:choices.append((len(route),slot,route))
            if choices:
                route=min(choices)[2]
                if route:return self.answer(raw,v,route[0],'carry_toward_goal_hypothesis')
        else:
            choices=[];y,x,h,w=self.goal['box'];perpendicular=0 if w>h else 1
            for target in sorted(cargo-slots):
                for a,m in sorted(self.motions.items()):
                    if m['delta'][perpendicular]==0:continue
                    approach=minus(target,m['delta']);route=self.route(v,approach)
                    if route is not None:choices.append((len(route),target,a,route))
            if choices and min(h,w)>v['n']:
                # Preserve established strip behavior. For a multi-row region,
                # select a grasp only when the learned motion hypothesis also
                # admits a delivery. Execute one actual action, then replan.
                choices=next(([item] for item in sorted(choices)
                              if self.delivery_possible(v,item[1],item[2],slots)),[])
            if choices:
                _,target,a,route=min(choices);self.target=target
                if route:return self.answer(raw,v,route[0],'approach_object')
                old=self.previous
                if old and old['action']==a and old['tag']=='orient_toward_object':
                    return self.answer(raw,v,aux[0],'pickup')
                return self.answer(raw,v,a,'orient_toward_object')
        # A completed spatial arrangement without actual progress refutes the
        # current interpretation; it must never manufacture a solved outcome.
        return dict(done=True,action=None,data={})
