"""Project the held object's pose when looking up observed failed movements."""
import copy
from carry_distributed_goal_learner_v2 import Controller as Base
from observed_transport_memory_v1 import add

class Controller(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.carry_failures={};self.projected_supports={}
    def record(self,raw,v):
        old=self.previous;self.projected_supports={}
        if old and old['view'] and v and old['raw']['state']==raw['state']=='NOT_FINISHED' and old['raw']['levels_completed']==raw['levels_completed'] and old['action'] in self.motions:
            at=tuple(old['view']['body']['box'][:2]);now=tuple(v['body']['box'][:2]);grasp=old.get('experiment_grasp')
            cargo=tuple(sorted(self.positions(old['view'])));key=(self.level,at,old['action'],cargo,grasp)
            if now==at and grasp is not None:
                self.carry_failures[key]=dict(level=self.level,pose=at,action=old['action'],cargo=cargo,grasp=grasp,support=old['t'])
            elif now!=at:self.carry_failures.pop(key,None)
        super().record(raw,v)
    def route(self,v,target,offset=None):
        if offset is None or self.transport_active():return super().route(v,target,offset)
        at=tuple(v['body']['box'][:2]);cargo=self.positions(v);loose=cargo-{add(at,offset)};records=[]
        for r in self.carry_failures.values():
            if r['level']!=self.level or r['grasp']!=offset:continue
            old_loose=set(r['cargo'])-{add(r['pose'],offset)}
            if old_loose==loose:records.append(r)
        if not records:return super().route(v,target,offset)
        # The older static search queries one root cargo configuration at
        # every hypothetical body position. Translate each real failed edge
        # into that query convention only after proving equal loose cargo
        # and grasp. This represents the moving object's future position.
        original=self.blocked
        projected={(r['pose'],r['action'],tuple(sorted(cargo))) for r in records}
        self.blocked=original|projected
        self.projected_supports.update({r['support']:copy.deepcopy(r) for r in records})
        try:return super().route(v,target,offset)
        finally:self.blocked=original
    def answer(self,raw,v,action,tag):
        if action==0 and raw['state']=='GAME_OVER':self.attachment=None
        response=super().answer(raw,v,action,tag)
        self.previous['experiment_grasp']=self.held
        if self.projected_supports:
            response['certificate']['projected_carry_collisions']=dict(records=[self.projected_supports[i] for i in sorted(self.projected_supports)],hypothesis='same_loose_objects_and_grasp_with_projected_held_pose')
        return response
