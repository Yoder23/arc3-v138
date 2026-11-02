"""Retain measured joint dynamics and replan instead of repeating static loops."""
from carry_interaction_learner_v7 import Controller as Base
from observed_joint_routes_v1 import Memory,state

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.joint_memory={}
    def key(self,offset):return (self.level,offset)
    def geometric_state(self,v):return state(v['body']['box'][:2],self.positions(v))
    def record(self,raw,v):
        old=self.previous;offset=self.held
        super().record(raw,v)
        if (old and old['view'] and v and self.held==offset
            and old['raw']['state']==raw['state']=='NOT_FINISHED'
            and old['raw']['levels_completed']==raw['levels_completed']
            and old['action'] in self.motions):
            model=self.joint_memory.setdefault(self.key(offset),Memory())
            model.observe(self.geometric_state(old['view']),old['action'],self.geometric_state(v),old['t'],offset)
        if raw['state']=='GAME_OVER' and not self.retain:self.joint_memory.clear()
    def route(self,v,target,offset=None):
        model=self.joint_memory.get(self.key(offset))
        if model is None or not model.dynamic:return super().route(v,target,offset)
        return model.route(self.geometric_state(v),target,{a:tuple(m['delta']) for a,m in self.motions.items()},v['n'],offset,self.blocked)
    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag)
        model=self.joint_memory.get(self.key(self.held))
        if model and model.dynamic and v:
            observed=model.observed(self.geometric_state(v),action)
            response['certificate']['joint_memory']=dict(
                hypothesis='observed_joint_transitions_with_static_unknown_edges',offset=self.held,
                supports=model.witnesses(),known_first_step=None if observed is None else dict(next_state=observed[0],support=observed[1]))
        return response
