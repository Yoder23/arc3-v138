"""Scope measured motion failures to the grasp hypothesis used for that action."""
import copy
from carry_transport_learner_v2 import Controller as Base

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.scoped_motion_failures=[]
    def record(self,raw,v):
        old=self.previous
        if old and old['view'] and v and 'planning_grasp_context' in old:
            if (old['raw']['state']==raw['state']=='NOT_FINISHED' and old['raw']['levels_completed']==raw['levels_completed']
                and old['action'] in self.motions and tuple(old['view']['body']['box'][:2])==tuple(v['body']['box'][:2])):
                self.scoped_motion_failures.append(dict(level=raw['levels_completed'],pose=tuple(v['body']['box'][:2]),
                    action=old['action'],cargo=tuple(sorted(self.positions(old['view']))),
                    grasp=old['planning_grasp_context'],support=old['t']))
        if raw['state']=='GAME_OVER' and not self.retain:self.scoped_motion_failures=[]
        super().record(raw,v)
    def route(self,v,target,offset=None):
        if not self.transport_active():return super().route(v,target,offset)
        original=self.blocked
        self.blocked={(r['pose'],r['action'],r['cargo']) for r in self.scoped_motion_failures
                      if r['level']==self.level and r['grasp']==offset}
        try:return super().route(v,target,offset)
        finally:self.blocked=original
    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag)
        if self.transport_active():
            response['certificate']['planning_grasp_context']=self.held
            response['certificate']['scoped_motion_failures']=copy.deepcopy([r for r in self.scoped_motion_failures if r['level']==self.level])
            self.previous['planning_grasp_context']=self.held
        return response
