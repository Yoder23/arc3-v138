"""Test shared blocked materials as delivery entries after ordinary plans fail."""
import copy
from carry_grasp_staging_v1 import Controller as Base
from carry_interaction_learner_v2 import Controller as Primitive
from observed_transport_memory_v1 import add,sub,feature
class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.material_trial=None;self.material_attempts=[]
    def material_candidates(self,raw,v):
        current=self.transport.barriers(self.level);past=[]
        for level in sorted({r['level']for r in self.transport.transports if r['level']!=self.level}):
            for look,supports in self.transport.barriers(level):
                if any(look==current_look for current_look,_ in current):past.append(dict(level=level,feature=look,blocked_sources=[i for i,_ in supports],transports=copy.deepcopy([r for r in self.transport.transports if r['level']==level])))
        if not past:return []
        at=tuple(v['body']['box'][:2]);offset=self.held;n=v['n'];cargo=self.positions(v);choices=[]
        tried={(r['level'],tuple(r['entry']))for r in self.material_attempts}
        for y in range(at[0]%n,64-n+1,n):
            for x in range(at[1]%n,64-n+1,n):
                entry=(y,x);look=feature(raw['frame'],entry,n)
                supports=[rows for f,rows in current if f==look]
                if not supports or entry in cargo or(self.level,entry)in tried:continue
                body=sub(entry,offset);path=self.route(v,body,offset)
                if path is None:continue
                choices.append((len(path),entry,path,dict(level=self.level,source=self.t,entry=entry,feature=look,blocked_sources=[i for i,_ in supports[0]],past=past,body=at,grasp=offset,path=path,hypothesis='test_shared_blocked_material_as_delivery_entry')))
        return choices
    def material_action(self,raw,v,action,tag):
        r=Primitive.answer(self,raw,v,action,tag);r['certificate']['material_entry_trial']=copy.deepcopy(self.material_trial);return r
    def continue_material(self,raw):
        p=self.material_trial;v=self.view(raw)
        if v is None:return None
        self.record(raw,v);self.previous=None
        at=tuple(v['body']['box'][:2]);entry=tuple(p['entry']);offset=tuple(p['grasp']);aux=[a for a in raw['available_actions']if a not in self.motions]
        if p['phase']=='carry':
            if self.held!=offset:return None
            path=self.route(v,sub(entry,offset),offset)
            if path is None:return None
            if path:return self.material_action(raw,v,path[0],'test_material_entry_route')
            if len(aux)!=1:return None
            p.update(phase='observe',released=self.t,probes=0);return self.material_action(raw,v,aux[0],'release')
        if p['phase']=='observe':
            if entry not in self.positions(v):
                p['movement_observed_at']=self.t;return None
            if p['probes']>=48:return None
            choices=[]
            for action,m in self.motions.items():
                q=add(at,m['delta']);path=self.route(v,q,self.held)
                if path and len(path)==1:
                    away=sum(abs(q[i]-entry[i])for i in(0,1));choices.append((0 if self.held is not None and sum(m['delta'][i]*offset[i]for i in(0,1))<0 else 1,self.trials[action],-away,action))
            if choices:
                p['probes']+=1;action=min(choices)[-1];return self.material_action(raw,v,action,'verify_drop'if self.held is not None else 'observe_material_entry')
        return None
    def respond(self,raw):
        if self.material_trial:
            if raw['state']=='NOT_FINISHED'and raw['levels_completed']==self.material_trial['level']:
                r=self.continue_material(raw)
                if r:return r
            self.material_attempts.append(copy.deepcopy(self.material_trial));self.material_trial=None
        r=super().respond(raw)
        if not r['done']or raw['state']!='NOT_FINISHED'or self.held is None or self.transport_active():return r
        v=self.view(raw)
        if v is None or not self.attachment:return r
        choices=self.material_candidates(raw,v)
        if not choices:return r
        _,entry,path,p=min(choices,key=lambda v:(v[0],v[1]));p['phase']='carry';self.material_trial=p
        if path:return self.material_action(raw,v,path[0],'test_material_entry_route')
        aux=[a for a in raw['available_actions']if a not in self.motions]
        if len(aux)!=1:return r
        p.update(phase='observe',released=self.t,probes=0);return self.material_action(raw,v,aux[0],'release')
