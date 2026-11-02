"""Test only reachable revised grasps; release remains an empirical hypothesis."""
import copy
from carry_interaction_learner_v11 import Controller as Base
from carry_interaction_learner_v2 import plus,minus

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.regrasp_pending=None;self.regrasp_trials=[]
    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag)
        if self.regrasp_pending:response['certificate']['regrasp_experiment']=copy.deepcopy(self.regrasp_pending)
        return response
    def respond(self,raw):
        pending=self.regrasp_pending
        if pending and (raw['state']!='NOT_FINISHED' or raw['levels_completed']!=self.level):
            self.regrasp_pending=None;pending=None
        if raw['state']=='GAME_OVER' and not self.retain:self.regrasp_trials=[]
        if pending and pending['phase']=='picked':
            self.regrasp_pending=None
            return super().respond(raw)
        if pending:
            v=self.view(raw)
            if v is None:
                self.regrasp_pending=None
                return super().respond(raw)
            self.record(raw,v)
            target=tuple(pending['target']);offset=tuple(pending['new_offset'])
            if target not in self.positions(v):
                # The release/identity hypothesis failed. Do not pretend the
                # original target stayed still or execute the rest blindly.
                self.regrasp_pending=None
                return dict(done=True,action=None,data={})
            aux=[a for a in raw['available_actions'] if a not in self.motions]
            if len(aux)!=1:self.regrasp_pending=None;return dict(done=True,action=None,data={})
            self.held=None;self.attachment=None;self.mode=None;self.target=target
            if pending['phase']=='oriented':
                pending['phase']='picked'
                return self.answer(raw,v,aux[0],'pickup')
            pending['phase']='approach'
            route=self.route(v,minus(target,offset))
            if route is None:self.regrasp_pending=None;return dict(done=True,action=None,data={})
            if route:return self.answer(raw,v,route[0],'regrasp_approach')
            pending['phase']='oriented'
            return self.answer(raw,v,pending['orientation_action'],'orient_toward_object')
        response=super().respond(raw)
        if not response['done'] or raw['state']!='NOT_FINISHED' or self.held is None or self.goal is None:return response
        v=self.view(raw)
        if v is None:return response
        at=tuple(v['body']['box'][:2]);target=plus(at,self.held)
        if target not in self.positions(v) or target in self.slots():return response
        trials=[r for r in self.regrasp_trials if r['level']==self.level]
        if len(trials)>=3:return response
        aux=[a for a in raw['available_actions'] if a not in self.motions]
        if len(aux)!=1:return response
        tried={tuple(r['new_offset']) for r in trials}|{tuple(self.held)}
        y,x,h,w=self.goal['box'];direction=(2*y+h-2*target[0],2*x+w-2*target[1])
        choices=[]
        for a,m in self.motions.items():
            offset=tuple(m['delta'])
            if offset in tried:continue
            approach=minus(target,offset)
            # This uses the already observed body, board and object geometry.
            # It predicts feasibility after release, not a verified release.
            path=self.route(v,approach)
            if path is None:continue
            choices.append((-sum(d*v for d,v in zip(direction,offset)),len(path),a,offset))
        if not choices:return response
        _,_,action,offset=min(choices)
        pending=dict(source=self.t,level=self.level,target=target,old_offset=self.held,new_offset=offset,
            orientation_action=action,phase='released',hypothesis='test_another_grasp_after_model_route_failure')
        self.regrasp_pending=pending;self.regrasp_trials.append(copy.deepcopy(pending))
        return self.answer(raw,v,aux[0],'release_for_regrasp')
