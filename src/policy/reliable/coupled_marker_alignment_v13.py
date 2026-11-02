import copy
from coupled_marker_alignment_base_v12 import Agent as Base,scene
from joint_compartment_planning_v4 import layout,search,advance,signature,conditioned
class Agent(Base):
    def __init__(self,prior=None):
        super().__init__(prior);self.transfer_evidence=[];self.joint=[];self.joint_expected=None;self.joint_previous=None;self.joint_level=None;self.joint_blocked=set()
    def respond(self,raw):
        old=self.previous;response=super().respond(raw)
        if response['done']:return response
        c=response['certificate'];s=c['scene'];g=self.geometry;L=layout(s,g)
        if L is None:return response
        state=(tuple(s['positions']),L['markers']);source=c['source'];bounds=[z['bounds']for z in g['segments']]
        if self.joint_level!=self.level:self.joint_level=self.level;self.joint=[];self.joint_expected=None;self.joint_previous=None;self.joint_blocked=set()
        if old and self.joint_previous:
            prior=self.joint_previous;before=prior['state']
            if before[1]!=state[1] and before[0]==state[0]:
                matches=[gate for gate in L['gates']if gate[0]==prior['index']and advance(before,gate[0],{},[gate],bounds)==state]
                if matches:self.transfer_evidence.append(dict(source=old['source'],index=prior['index'],before=before,after=state,gate=matches[0],fluid_side=g['segments'][matches[0][1]]['side'],markers=[p['ink']for p in s['pairs']],data=old['scene']['buttons'][prior['index']]['point']))
            if self.joint_expected is not None and state!=self.joint_expected:
                self.joint_blocked.add(signature(before,prior['index'],self.models,L['gates']));self.joint=[]
                self.failures.append(dict(source=old['source'],kind='joint_prediction_failed',expected=self.joint_expected,actual=state,index=prior['index']))
        index=None;tag=None;planned=None
        if self.transfer_evidence:
            unknown=[i for i,b in enumerate(s['buttons'])if b['box'][2]==b['box'][3]and i not in self.models and self.visits[(tuple(s['positions']),i)]==0]
            if unknown:index=unknown[0];tag='retest_unmodeled_control_in_new_context';self.joint=[]
            else:
                if not self.joint:self.joint=search(s['positions'],conditioned(L,self.transfer_evidence,self.geometry),self.models,bounds,self.joint_blocked)or search(s['positions'],L,self.models,bounds,self.joint_blocked)or[]
                if self.joint:index,planned=self.joint.pop(0);tag='compose_boundary_and_marker_transport'
        if index is not None:
            response['action']=6;response['data']=s['buttons'][index]['point'];c['index']=index;c['tag']=tag;c['plan']=None
            self.previous['index']=index;self.tried[index]+=1;self.visits[(tuple(s['positions']),index)]+=1
        else:index=c['index']
        self.joint_expected=planned;self.joint_previous=dict(state=state,index=index)
        c['transfer_evidence']=copy.deepcopy(self.transfer_evidence);c['joint_layout']=copy.deepcopy(L);c['joint_prediction']=planned;c['joint_remaining']=len(self.joint)
        return response
