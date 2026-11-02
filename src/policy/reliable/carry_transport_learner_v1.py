"""Use witnessed autonomous deliveries as testable intermediate subgoals."""
from collections import deque
import copy
from carry_context_refinement_v1 import Controller as Base
from observed_transport_memory_v1 import Memory,feature,add,sub

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.transport=Memory();self.transport_waits=0
    def record(self,raw,v):
        old=self.previous;offset=self.held
        # Observe before the base class changes its attachment or motion model.
        if old and old['view'] and v:
            self.transport.observe(old['raw'],raw,old['view']['cargo'],v['cargo'],old['view']['body'],v['body'],
                old['action'],old['t'],self.motions,Base.slots(self),offset)
        elif old:self.transport.boundary(raw['levels_completed'])
        if raw['state']=='GAME_OVER' and not self.retain:self.transport.boundary(raw['levels_completed'],True)
        super().record(raw,v)
    def transport_active(self):
        return bool(self.transport.entries(self.level) and self.transport.barriers(self.level))
    def slots(self):
        original=super().slots()
        return original|self.transport.entries(self.level) if self.transport_active() else original
    def route(self,v,target,offset=None):
        if not self.transport_active():return super().route(v,target,offset)
        start=tuple(v['body']['box'][:2]);loose=self.positions(v);n=v['n']
        if offset is not None:loose.discard(add(start,offset))
        raw=self._route_frame;barriers={look for look,_ in self.transport.barriers(self.level)}
        todo=deque([start]);previous={start:None};target=tuple(target)
        while todo and len(previous)<2500:
            p=todo.popleft()
            if p==target:break
            for a,m in sorted(self.motions.items()):
                q=add(p,m['delta']);held=None if offset is None else add(q,offset)
                if q in previous or q in loose or not all(0<=x<=64-n for x in q):continue
                if feature(raw,q,n) in barriers:continue
                if held is not None and (held in loose or not all(0<=x<=64-n for x in held)):continue
                if (p,a,tuple(sorted(self.positions(v)))) in self.blocked:continue
                if (self.level,p,a) in getattr(self,'blind_entries',set()):continue
                previous[q]=(p,a);todo.append(q)
        if target not in previous:return None
        out=[];p=target
        while previous[p] is not None:p,a=previous[p];out.append(a)
        return out[::-1]
    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag)
        if self.transport_active():
            response['certificate']['transport_memory']=dict(
                hypothesis='test_prior_observed_delivery_entry_after_body_barrier_evidence',
                transports=copy.deepcopy([r for r in self.transport.transports if r['level']==self.level]),
                barriers=[dict(feature=look,supports=[i for i,_ in rows]) for look,rows in self.transport.barriers(self.level)])
        return response
    def respond(self,raw):
        self._route_frame=raw['frame'];response=super().respond(raw)
        if response['done'] and raw['state']=='NOT_FINISHED' and self.transport_active() and self.transport.paths and self.transport_waits<32:
            v=self.view(raw)
            if v and self.held is None:
                p=tuple(v['body']['box'][:2])
                for a,m in sorted(self.motions.items(),key=lambda item:(self.trials[item[0]],item[0])):
                    path=self.route(v,add(p,m['delta']))
                    if path and len(path)==1:
                        self.transport_waits+=1
                        return self.answer(raw,v,a,'observe_pending_transport')
        return response
