"""Compose independent delivery attempts instead of waiting idly for each one."""
import copy
from carry_material_transfer_v1 import Controller as Base
from carry_grasp_staging_v1 import moved
from observed_transport_memory_v1 import add,sub,feature
class Controller(Base):
    def material_candidates(self,raw,v):
        attempts=self.material_attempts;self.material_attempts=[]
        try:options=super().material_candidates(raw,v)
        finally:self.material_attempts=attempts
        cargo=self.positions(v);remaining=self.slots()-cargo;n=v['n']
        return [(length+min((sum(abs(entry[k]-goal[k])for k in(0,1))//n for goal in remaining),default=0),entry,path,p)for length,entry,path,p in options]
    def continue_material(self,raw):
        p=self.material_trial
        if p['phase']not in('approach','orient','verify_pick'):
            if p['phase']=='observe'and p['probes']>=1:
                v=self.view(raw)
                if v:
                    self.record(raw,v);self.previous=None
                    if self.held is None:p['release_verified_at']=self.t;return None
            return super().continue_material(raw)
        v=self.view(raw)
        if not v:return None
        self.record(raw,v);self.previous=None;at=tuple(v['body']['box'][:2]);offset=tuple(p['grasp']);target=tuple(p['cargo']);aux=[a for a in raw['available_actions']if a not in self.motions]
        if p['phase']=='verify_pick':
            if self.held==offset:p['phase']='carry';return super().continue_material(raw)
            choices=[]
            for action,m in self.motions.items():
                path=self.route(v,add(at,m['delta']),offset)
                if path and len(path)==1:choices.append((sum(m['delta'][k]*offset[k]for k in(0,1)),action))
            if choices:return self.material_action(raw,v,min(choices)[1],'verify_pick')
            return None
        if target not in self.positions(v):return None
        path=self.route(v,sub(target,offset))
        if path is None:return None
        if path:p['phase']='approach';return self.material_action(raw,v,path[0],'approach_object')
        if p['phase']=='approach':p['phase']='orient';return self.material_action(raw,v,p['orientation'],'orient_toward_object')
        if len(aux)!=1:return None
        p['phase']='verify_pick';return self.material_action(raw,v,aux[0],'pickup')
    def respond(self,raw):
        if self.material_trial:return super().respond(raw)
        if raw['state']!='NOT_FINISHED'or raw['levels_completed']!=self.level:return super().respond(raw)
        if self.transport_active():return super().respond(raw)
        v=self.view(raw)
        if not v or len(self.motions)!=4 or not self.transport.barriers(self.level):return super().respond(raw)
        self.record(raw,v);self.previous=None
        if self.held is not None:
            options=self.material_candidates(raw,v)
            if options:
                _,entry,path,p=min(options,key=lambda z:(z[0],len(z[2]),z[1]));p['phase']='carry';self.material_trial=p
                return self.continue_material(raw)or super().respond(raw)
        else:
            at=tuple(v['body']['box'][:2]);cargo=self.positions(v);goals=self.slots();choices=[];looks={look for look,_ in self.transport.barriers(self.level)}
            for target in sorted(cargo-goals):
                if feature(raw['frame'],target,v['n'])in looks:continue
                for orientation,m in sorted(self.motions.items()):
                    offset=tuple(m['delta']);approach=sub(target,offset);path=self.route(v,approach)
                    if path is None:continue
                    hypothetical=moved(v,approach);old=self.held;self.held=offset
                    try:options=self.material_candidates(raw,hypothetical)
                    finally:self.held=old
                    for cost,entry,delivery,p in options:
                        p.update(phase='approach',cargo=target,orientation=orientation,source=self.t,body=at)
                        choices.append((len(path)+cost+3,len(path),target,orientation,p))
            if choices:
                self.material_trial=min(choices,key=lambda z:z[:4])[-1]
                return self.continue_material(raw)or super().respond(raw)
        return super().respond(raw)
