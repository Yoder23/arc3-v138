"""Local attachment hypothesis remains valid when an additional object moves.

This component does not yet plan a coupled object's destination. It preserves
the independently observed local co-motion instead of requiring the rest of
the scene to stay fixed.
"""
import copy
from carry_interaction_learner_v6 import Controller as Base
from carry_interaction_learner_v2 import plus,minus

class Controller(Base):
    def record(self,raw,v):
        old=self.previous
        if old and v and old['view'] and raw['levels_completed']==old['raw']['levels_completed'] and old['action']!=0:
            before=old['view'];delta=minus(v['body']['box'][:2],before['body']['box'][:2]);a=old['action']
            self.history.append(dict(before=old['raw'],action=a,after=copy.deepcopy(raw)))
            if delta!=(0,0):
                if (delta[0]==0) != (delta[1]==0):
                    earlier=self.motions.get(a)
                    if earlier is None:self.motions[a]=dict(delta=delta,support=old['t'])
                    elif tuple(earlier['delta'])!=delta:self.motions.pop(a,None)
                before_pos=self.positions(before);after_pos=self.positions(v)
                movers=[p for p in before_pos if p not in after_pos and plus(p,delta) in after_pos]
                if len(movers)==1:
                    offset=minus(movers[0],before['body']['box'][:2]);self.held=offset
                    self.attachment=dict(support=old['t'],offset=offset)
                elif old['tag']=='verify_drop':self.held=None;self.attachment=None
                elif self.held is not None:self.held=None;self.attachment=None
                if old['tag'] in ('verify_pick','verify_drop'):self.mode=None
            elif a in self.motions:
                self.blocked.add((tuple(before['body']['box'][:2]),a,tuple(sorted(self.positions(before)))))
            if old['tag']=='pickup':self.mode='verify_pick'
            elif old['tag']=='release':self.mode='verify_drop'
        if v and self.goal is None and len(v['containers'])==1:
            container=v['containers'][0]
            self.goal=dict(box=tuple(container['box']),inner_ink=container['inner_ink'],frame_ink=container['frame_ink'],observed_at=self.t,hypothesis='tile_container_with_repeated_objects')

