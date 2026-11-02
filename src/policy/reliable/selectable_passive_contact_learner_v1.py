"""A bounded contact experiment after a single-body goal does not finish the task."""
import copy
from collections import Counter,deque
from selectable_multi_object_learner_v24 import Agent as Base
from selectable_rect_core_v1 import inside
from visible_passive_components_v1 import components
class Agent(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.passive_probe_state=None;self.learned_passive_effects=[]
    def reset_level(self,raw):super().reset_level(raw);self.passive_probe_state=None
    def candidates(self,raw):
        bg=Counter(raw['frame'][y][x] for y,x in ((0,0),(0,63),(63,0),(63,63))).most_common(1)[0][0];excluded={bg,self.palette,self.floor}|{g['ink'] for g in self.goals}
        return [q for q in components(raw['frame']) if q['ink'] not in excluded and 4<=len(q['shape'])<=144 and 0<q['box'][0] and 0<q['box'][1] and q['box'][0]+q['box'][2]<64 and q['box'][1]+q['box'][3]<64]
    def contact_route(self,raw,body,target):
        cells={(target['box'][0]+y,target['box'][1]+x) for y,x in target['shape']};h,w=body['box'][2:];start=tuple(body['box'][:2]);todo=deque([start]);parents={start:None};allowed={self.floor}|{g['ink'] for g in self.goals}
        while todo:
            at=todo.popleft()
            for a,m in sorted(self.motions.items()):
                dy,dx=m['delta'];q=(at[0]+dy,at[1]+dx)
                if not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
                pixels={(y,x) for y in range(q[0],q[0]+h) for x in range(q[1],q[1]+w)}
                if pixels&cells:
                    path=[a];cursor=at
                    while parents[cursor] is not None:prev,act=parents[cursor];path.append(act);cursor=prev
                    return path[::-1]
                if q in parents or any(not inside((y,x),body['box']) and raw['frame'][y][x] not in allowed for y,x in pixels):continue
                parents[q]=(at,a);todo.append(q)
        return None
    def respond(self,raw):
        if self.passive_probe_state is None:
            r=super().respond(raw)
            if not r['done'] or raw['state']!='NOT_FINISHED' or len(self.objects)!=1 or not self.motions:return r
            body=self.objects[0];choices=[]
            for target in self.candidates(raw):
                path=self.contact_route(raw,body,target)
                if path:choices.append((len(path),tuple(target['box']),target))
            if not choices:return r
            self.passive_probe_state=dict(target=copy.deepcopy(min(choices,key=lambda q:q[:2])[2]),steps=0,contact=None)
        else:
            if raw['state']!='NOT_FINISHED' or self.level!=raw['levels_completed']:self.passive_probe_state=None;return super().respond(raw)
            self.observe(raw)
        state=self.passive_probe_state
        if state['contact']:
            if state['contact'].get('processed'):return dict(done=True,action=None,data={},learned_passive_effects=copy.deepcopy(self.learned_passive_effects))
            state['contact']['processed']=True
            old=state['contact'];before=old['target'];prior=old['candidates'];now=self.candidates(raw)
            added=[q for q in now if q['ink']==before['ink'] and q['shape']==before['shape'] and not any(q['box']==p['box'] and q['ink']==p['ink'] for p in prior)]
            if len(added)==1:
                after=added[0];delta=tuple(after['box'][i]-before['box'][i] for i in (0,1));actor=next((b for b in self.objects if tuple(b['box'])==tuple(old['actor']['box'])),None)
                if (delta[0]==0)!=(delta[1]==0):self.learned_passive_effects.append(dict(source=old['source'],action=old['action'],before=before,after=copy.deepcopy(after),delta=delta,actor_before=old['actor'],actor_after=copy.deepcopy(actor),outcome='observed_other_component_translation',causality_is_hypothesis=True))
            return dict(done=True,action=None,data={},learned_passive_effects=copy.deepcopy(self.learned_passive_effects))
        if state['steps']>=64 or len(self.objects)!=1:return dict(done=True,action=None,data={},learned_passive_effects=copy.deepcopy(self.learned_passive_effects))
        body=self.objects[0];target=state['target'];path=self.contact_route(raw,body,target)
        if not path:return dict(done=True,action=None,data={},learned_passive_effects=copy.deepcopy(self.learned_passive_effects))
        if len(path)==1:state['contact']=dict(source=self.t,action=path[0],target=copy.deepcopy(target),actor=copy.deepcopy(body),candidates=copy.deepcopy(self.candidates(raw)))
        r=self.answer(raw,path[0],{},'test_passive_component_contact' if len(path)==1 else 'approach_passive_component',body,path);state['steps']+=1
        if not r['done']:r['certificate']['passive_contact_hypothesis']=dict(target=copy.deepcopy(target),route=path,interaction_unconfirmed=True)
        return r
