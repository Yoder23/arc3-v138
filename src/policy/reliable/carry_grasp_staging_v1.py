"""Compose a carrying move before a currently impossible release/regrasp."""
import copy
from carry_regrasp_revision_v3 import Controller as Base
from observed_transport_memory_v1 import add,sub

def moved(v,pose,offset=None):
    v=copy.deepcopy(v);b=v['body'];old=tuple(b['box'][:2]);delta=sub(pose,old)
    b['box']=pose+tuple(b['box'][2:]);b['fill_box']=add(tuple(b['fill_box'][:2]),delta)+tuple(b['fill_box'][2:])
    if offset is not None:
        parts=[c for c in v['cargo'] if tuple(c['box'][:2])==add(old,offset)];assert len(parts)==1
        parts[0]['box']=add(pose,offset)+tuple(parts[0]['box'][2:])
    return v

def alternatives(agent,v):
    at=tuple(v['body']['box'][:2]);target=add(at,agent.held);cargo=agent.positions(v);choices=[]
    for action,m in sorted(agent.motions.items()):
        offset=tuple(m['delta'])
        if offset==agent.held:continue
        approach=sub(target,offset);path=agent.route(v,approach)
        if path is None:continue
        hypothetical=moved(v,approach)
        for slot in sorted(agent.slots()-(cargo-{target})):
            delivery=agent.route(hypothetical,sub(slot,offset),offset)
            if delivery is not None:choices.append((len(path)+len(delivery)+3,action,offset,path,slot,delivery))
    return choices

class Controller(Base):
    def respond(self,raw):
        response=super().respond(raw)
        if not response['done'] or raw['state']!='NOT_FINISHED' or self.held is None or not self.attachment or self.goal is None or self.transport_active():return response
        v=self.view(raw)
        if v is None or alternatives(self,v):return response
        at=tuple(v['body']['box'][:2]);candidates=[]
        for action,m in sorted(self.motions.items()):
            pose=add(at,tuple(m['delta']));path=self.route(v,pose,self.held)
            if not path or len(path)>3:continue
            hypothetical=moved(v,pose,self.held)
            for cost,orient,offset,approach,goal,delivery in alternatives(self,hypothetical):
                candidates.append((len(path)+cost,pose,path,orient,offset,approach,goal,delivery))
        if not candidates:return response
        _,pose,path,orient,offset,approach,goal,delivery=min(candidates)
        plan=dict(observed_at=self.t,body=at,cargo=sorted(self.positions(v)),grasp=self.held,stage_body=pose,carrying_path=path,orientation_action=orient,new_grasp=offset,approach=approach,goal=goal,delivery=delivery,hypothesis='move_attached_object_before_releasing_to_create_grasp_access')
        response=self.answer(raw,v,path[0],'stage_for_regrasp');response['certificate']['grasp_staging']=plan
        return response
