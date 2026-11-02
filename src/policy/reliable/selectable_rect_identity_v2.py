"""Revise goal assignments with bounded joint-body search and observed failure rules."""
import copy,heapq,itertools
from collections import Counter
from selectable_rect_core_v1 import Agent as Base,inside
class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.identities={};self.constraint_hypotheses=[];self.joint_mode=False;self.disable_joint=False;self.joint_diagnostics=[];self.identity_links=[];self.identity_last_seen={}
    def reset_level(self,raw):
        super().reset_level(raw);self.identities={};self.constraint_hypotheses=[];self.joint_mode=False;self.identity_links=[];self.identity_last_seen={}
    def observe(self,raw):
        old=self.previous;old_objects=copy.deepcopy(self.objects);old_ids=dict(self.identities);nfail=len(self.failures)
        result=super().observe(raw)
        if not result:return result
        if not self.identities:self.identities={tuple(o['box']):i for i,o in enumerate(self.objects)}
        else:
            removed=[o for o in old_objects if tuple(o['box']) not in [tuple(q['box']) for q in self.objects]];added=[q for q in self.objects if tuple(q['box']) not in [tuple(o['box']) for o in old_objects]]
            if len(removed)==len(added)==1 and removed[0]['box'][2:]==added[0]['box'][2:]:
                key=tuple(removed[0]['box']);ident=self.identities.pop(key,None)
                if ident is not None:self.identities[tuple(added[0]['box'])]=ident
        present={tuple(o['box']) for o in self.objects}
        for body in self.objects:
            box=tuple(body['box'])
            if box not in self.identities:
                candidates=[b for b in self.identities if b not in present and b[2:]==box[2:]]
                if len(candidates)==1:
                    previous=candidates[0];ident=self.identities.pop(previous);mode='unique_shape_reassociation_hypothesis';prior=self.identity_last_seen.get(ident)
                else:
                    ident=max(self.identities.values(),default=-1)+1;mode='fresh_observation_label';prior=None
                self.identities[box]=ident;self.identity_links.append(dict(identity=ident,observed_at=self.t,body=copy.deepcopy(body),prior=copy.deepcopy(prior),mode=mode,physical_identity_confirmed=False))
            self.identity_last_seen[self.identities[box]]=dict(observed_at=self.t,body=copy.deepcopy(body))
        if old and len(self.failures)>nfail:
            f=self.failures[-1];y,x=f['destination'];h,w=f['body']['box'][2:];others=[o for o in old_objects if tuple(o['box'])!=tuple(f['body']['box'])]
            if old['action'] in self.motions and not any(inside((yy,xx),o['box']) for yy in range(y,y+h) for xx in range(x,x+w) for o in others):
                ident=old_ids.get(tuple(f['body']['box']))
                if ident is not None:
                    self.constraint_hypotheses.append(dict(source=f['source'],identity=ident,body=copy.deepcopy(f['body']),delta=tuple(self.motions[old['action']]['delta']),pattern=f['context'][0],destination=f['destination'],hypothesis='body_specific_destination_pattern_may_block_motion',causality_confirmed=False))
        return result
    def answer(self,raw,a,d,tag,target=None,route=None,goal=None):
        result=super().answer(raw,a,d,tag,target,route,goal)
        result['certificate']['identities']=[dict(identity=self.identities[tuple(o['box'])],body=copy.deepcopy(o)) for o in self.objects]
        result['certificate']['constraint_hypotheses']=copy.deepcopy(self.constraint_hypotheses)
        result['certificate']['joint_assignment_revision']=self.joint_mode;result['certificate']['identity_links']=copy.deepcopy(self.identity_links)
        return result
    def joint_response(self,raw):
        found=self.joint_plan(raw)
        if not found or not found[1]:return dict(done=True,action=None,data={})
        bodies,moves=found;i,a=moves[0];body=bodies[i]
        if tuple(body['box'])!=tuple(self.active_box or ()):
            y,x,h,w=body['box'];return self.answer(raw,6,dict(x=x+w//2,y=y+h//2),'joint_select_intermediate_body',body,[a])
        return self.answer(raw,a,{},'joint_intermediate_action',body,[a])
    def respond(self,raw):
        if self.joint_mode and self.level==raw['levels_completed'] and raw['state']=='NOT_FINISHED':
            if not self.observe(raw):return dict(done=True,action=None,data={})
            return self.joint_response(raw)
        response=super().respond(raw)
        if response['done'] and raw['state']=='NOT_FINISHED' and not self.disable_joint:
            self.joint_mode=True;return self.joint_response(raw)
        return response
