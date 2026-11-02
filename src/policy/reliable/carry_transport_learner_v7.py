"""Observe a just-released transport entry before declaring no work remains."""
import copy
from carry_transport_learner_v5 import Controller as Base
from observed_transport_memory_v1 import add

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.pending_delivery=None;self.delivery_releases={}
    def record(self,raw,v):
        old=self.previous;held=self.held
        super().record(raw,v)
        if raw['state']!='NOT_FINISHED' or (self.pending_delivery and self.pending_delivery['level']!=self.level):self.pending_delivery=None
        if not self.transport_active() or not old or not old['view'] or not v:return
        if old['tag']=='release' and held is not None:
            point=add(old['view']['body']['box'][:2],held)
            if point in self.transport.entries(self.level):
                self.pending_delivery=dict(level=self.level,release=old['t'],point=point,probes=0)
        p=self.pending_delivery
        if not p:return
        if tuple(p['point']) not in self.positions(v):self.pending_delivery=None;return
        if old['tag']=='verify_drop' and self.held is None and tuple(p['point']) in self.positions(old['view']):
            if old['view']['body']['box'][:2]!=v['body']['box'][:2]:p['verification']=old['t']
        if 'verification' in p:self.delivery_releases[p['release']]=copy.deepcopy(p)
    def latency(self):
        supports=[]
        for r in self.delivery_releases.values():
            if r['level']!=self.level:continue
            candidates=[t for t in self.transport.transports if t['level']==self.level and tuple(t['start'])==tuple(r['point']) and t['first']>r['verification']]
            if candidates:
                t=min(candidates,key=lambda t:t['first'])
                supports.append(dict(release=r['release'],verification=r['verification'],point=r['point'],transport_first=t['first'],delay=t['first']-r['release']))
        limit=min(32,max([4]+[r['delay']+2 for r in supports]))
        return limit,supports
    def respond(self,raw):
        response=super().respond(raw);p=self.pending_delivery;limit,supports=self.latency()
        if (not response['done'] or raw['state']!='NOT_FINISHED' or not self.transport_active()
            or self.held is not None or not p or 'verification' not in p or p['probes']>=limit):return response
        v=self.view(raw)
        if not v or tuple(p['point']) not in self.positions(v):return response
        at=tuple(v['body']['box'][:2])
        for action,m in sorted(self.motions.items(),key=lambda item:(self.trials[item[0]],item[0])):
            path=self.route(v,add(at,m['delta']))
            if path and len(path)==1:
                p['probes']+=1;response=self.answer(raw,v,action,'observe_delayed_delivery')
                response['certificate']['pending_delivery']=dict(copy.deepcopy(p),probe_limit=limit,latency_supports=copy.deepcopy(supports))
                return response
        return response
