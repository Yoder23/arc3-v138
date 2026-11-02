"""Revise an actually failed approach without discarding the released object."""
import copy
from carry_projected_collision_v2 import Controller as Base
from observed_transport_memory_v1 import add,sub

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.approach_failures={};self.approach_revision=None

    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag);p=self.regrasp_pending;r=self.approach_revision
        if p and r and p['source']==r['release_source'] and tuple(p['new_offset'])==tuple(r['new_offset']):
            response['certificate']['regrasp_revision']=copy.deepcopy(r)
        return response

    def respond(self,raw):
        pending=copy.deepcopy(self.regrasp_pending)
        if raw['state']=='GAME_OVER' and not self.retain:self.approach_failures={}
        response=super().respond(raw)
        if not response['done'] or raw['state']!='NOT_FINISHED' or not pending or pending['phase'] not in ('released','approach'):return response
        # The inherited branch already consumed the actual transition. Do not
        # call record() again and accidentally count the same failure twice.
        v=self.view(raw);old=self.previous
        if v is None or old is None or old['view'] is None:return response
        if old['tag']!='regrasp_approach' or old['action'] not in self.motions:return response
        if old['raw']['state']!='NOT_FINISHED' or old['raw']['levels_completed']!=raw['levels_completed']:return response
        at=tuple(v['body']['box'][:2]);target=tuple(pending['target']);failed=tuple(pending['new_offset']);cargo=self.positions(v)
        if at!=tuple(old['view']['body']['box'][:2]) or target not in cargo:return response
        if self.route(v,sub(target,failed)) is not None:return response
        key=(self.level,target,tuple(sorted(cargo)),tuple(pending['old_offset']))
        failures=self.approach_failures.setdefault(key,{})
        failures[failed]=dict(support=old['t'],pose=at,action=old['action'],offset=failed)
        alternatives=[]
        for action,m in sorted(self.motions.items()):
            offset=tuple(m['delta'])
            if offset in failures or offset==tuple(pending['old_offset']):continue
            approach=sub(target,offset);path=self.route(v,approach)
            if path is None:continue
            hypothetical=copy.deepcopy(v);b=hypothetical['body'];delta=sub(approach,at)
            b['box']=approach+tuple(b['box'][2:]);b['fill_box']=add(tuple(b['fill_box'][:2]),delta)+tuple(b['fill_box'][2:])
            deliveries=[]
            for slot in sorted(self.slots()-(cargo-{target})):
                route=self.route(hypothetical,sub(slot,offset),offset)
                if route is not None:deliveries.append((len(route),slot,route))
            if not deliveries:continue
            length,slot,delivery=min(deliveries)
            alternatives.append((len(path)+length+2,len(path),action,offset,path,slot,delivery))
        if not alternatives:return response
        _,_,action,offset,path,slot,delivery=min(alternatives)
        revision=dict(release_source=pending['source'],observed_at=self.t,level=self.level,target=target,cargo=tuple(sorted(cargo)),
            failed_offset=failed,new_offset=offset,orientation_action=action,failed_approaches=[copy.deepcopy(failures[k]) for k in sorted(failures)],
            approach=path,delivery=delivery,goal_slot=slot,hypothesis='revise_a_failed_approach_with_retained_context')
        pending.update(new_offset=offset,orientation_action=action,phase='approach' if path else 'oriented')
        self.regrasp_pending=pending;self.regrasp_trials.append(copy.deepcopy(pending));self.approach_revision=revision
        return self.answer(raw,v,path[0] if path else action,'regrasp_approach' if path else 'orient_toward_object')
