"""Separate unheld obstacles from carrying failures before projecting them."""
import copy
from carry_projected_collision_v1 import Controller as Prior
from carry_distributed_goal_learner_v2 import Controller as Unprojected
from observed_transport_memory_v1 import add

class Controller(Prior):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.used_grasp_scope=False
    def record(self,raw,v):self.used_grasp_scope=False;super().record(raw,v)
    def route(self,v,target,offset=None):
        if offset is None or self.transport_active():return Unprojected.route(self,v,target,offset)
        at=tuple(v['body']['box'][:2]);cargo=self.positions(v);loose=cargo-{add(at,offset)}
        records=[r for r in self.carry_failures.values() if r['level']==self.level and r['grasp']==offset and set(r['cargo'])-{add(r['pose'],offset)}==loose]
        original=self.blocked
        # An unheld actor was blocked by this object before pickup. That is
        # not evidence that actor plus attached object cannot move together.
        self.blocked={(r['pose'],r['action'],tuple(sorted(cargo))) for r in records}
        self.projected_supports.update({r['support']:copy.deepcopy(r) for r in records})
        self.used_grasp_scope|=offset==self.held
        try:return Unprojected.route(self,v,target,offset)
        finally:self.blocked=original
    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag)
        if self.used_grasp_scope and self.held is not None and self.attachment:
            response['certificate']['grasp_scoped_static_search']=dict(grasp=self.held,attachment_source=self.attachment['support'],hypothesis='distinguish_unheld_and_attached_transition_contexts')
        return response
