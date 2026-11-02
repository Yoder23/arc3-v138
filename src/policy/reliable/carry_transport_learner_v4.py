"""Compare a complete regrasp-and-delivery hypothesis with carrying detours."""
import copy
from carry_transport_learner_v3 import Controller as Base
from observed_transport_memory_v1 import add,sub

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.grasp_cost_cache=None
    def costs(self,v):
        key=(self.level,self.t,tuple(v['body']['box'][:2]),self.held)
        if self.grasp_cost_cache and self.grasp_cost_cache['key']==key:return self.grasp_cost_cache
        at=tuple(v['body']['box'][:2]);target=add(at,self.held);slots=self.slots();cargo=self.positions(v)
        direct=[]
        for slot in sorted(slots-(cargo-{target})):
            path=Base.route(self,v,sub(slot,self.held),self.held)
            if path is not None:direct.append((len(path),slot,path))
        alternatives=[]
        for action,motion in sorted(self.motions.items()):
            offset=tuple(motion['delta'])
            if offset==self.held:continue
            approach=sub(target,offset);path=Base.route(self,v,approach)
            if path is None:continue
            hypothetical=copy.deepcopy(v);hypothetical['body']['box']=approach+tuple(v['body']['box'][2:])
            for slot in sorted(slots-(cargo-{target})):
                delivery=Base.route(self,hypothetical,sub(slot,offset),offset)
                if delivery is None:continue
                # Release, orient, pickup and one verification action are
                # prospective costs, not claims that these actions succeeded.
                alternatives.append((len(path)+len(delivery)+4,action,slot,offset,path,delivery))
        best=min(alternatives) if alternatives else None;current=min(direct) if direct else None
        better=bool(best and (current is None or best[0]+4<current[0]))
        result=dict(key=key,better=better,body=at,object=target,direct=current,alternative=best,margin=4)
        self.grasp_cost_cache=result;return result
    def route(self,v,target,offset=None):
        if not self.transport_active() or self.held is None:return super().route(v,target,offset)
        actual=self.view(dict(frame=self._route_frame,state='NOT_FINISHED',available_actions=list(self.motions),levels_completed=self.level))
        if actual is None or tuple(actual['body']['box'][:2])!=tuple(v['body']['box'][:2]):return super().route(v,target,offset)
        at=tuple(v['body']['box'][:2]);object_at=add(at,self.held)
        if offset==self.held and add(target,offset) in self.slots():
            plan=self.costs(v)
            if plan['better']:return None
        cache=self.grasp_cost_cache
        if offset is None and cache and cache['key']==(self.level,self.t,at,self.held) and cache['better']:
            requested=sub(object_at,target)
            if requested in {tuple(m['delta']) for m in self.motions.values()} and requested!=cache['alternative'][3]:return None
        return super().route(v,target,offset)
    def answer(self,raw,v,action,tag):
        plan=self.grasp_cost_cache
        response=super().answer(raw,v,action,tag)
        if tag=='release_for_regrasp' and plan and plan['better'] and plan['key'][1]==self.t-1:
            response['certificate']['grasp_cost_revision']=dict(source=self.t-1,body=plan['body'],object=plan['object'],
                direct=copy.deepcopy(plan['direct']),alternative=copy.deepcopy(plan['alternative']),margin=plan['margin'],
                hypothesis='prefer_shorter_complete_regrasp_delivery_under_observed_model')
        return response
