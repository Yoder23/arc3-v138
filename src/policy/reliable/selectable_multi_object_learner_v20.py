"""When learned plans fail, approach another body and test an unknown interaction."""
import copy
from collections import deque,Counter
from selectable_multi_object_learner_v19 import Agent as Base
from selectable_rect_push_core_v2 import overlap
from selectable_rect_core_v1 import inside
class Agent(Base):
    def contact_plan(self,raw,body,other):
        h,w=body['box'][2:];start=tuple(body['box'][:2]);identity=self.identities[tuple(body['box'])];others=[q for q in self.objects if q is not body]
        bg=Counter(raw['frame'][y][x] for y,x in ((0,0),(0,63),(63,0),(63,63))).most_common(1)[0][0];allowed=(set(v for row in raw['frame'] for v in row)-{bg,self.palette})|{self.floor}
        todo=deque([start]);parents={start:None}
        def history(at,a):
            path=[a]
            while parents[at] is not None:prev,act=parents[at];path.append(act);at=prev
            return path[::-1]
        while todo:
            at=todo.popleft()
            for a,m in sorted(self.motions.items()):
                dy,dx=m['delta'];q=(at[0]+dy,at[1]+dx)
                if not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
                hit=[o for o in others if overlap((*q,h,w),o['box'])]
                if hit:
                    if len(hit)==1 and hit[0] is other and (self.level,(*at,h,w),tuple(other['box']),a) not in self.contact_inquiries:return history(at,a)
                    continue
                if q in parents:continue
                pattern=self.context(raw,q,self.objects,body)[0]
                if any(v not in allowed for v in pattern):continue
                if any(c['identity']==identity and tuple(c['delta'])==tuple(m['delta']) and tuple(c['pattern'])==tuple(pattern) for c in self.constraint_hypotheses):continue
                parents[q]=(at,a);todo.append(q)
        return None
    def joint_response(self,raw):
        response=super().joint_response(raw)
        if not response['done'] or self.push_memory or self.disable_push or len(self.motions)<2:return response
        choices=[]
        for body in self.objects:
            for other in self.objects:
                if body is other:continue
                path=self.contact_plan(raw,body,other)
                if path:choices.append((len(path)+(tuple(body['box'])!=tuple(self.active_box or ())),tuple(body['box']),tuple(other['box']),body,other,path))
        if not choices:return response
        _,_,_,body,other,path=min(choices,key=lambda q:q[:3]);y,x,h,w=body['box']
        if tuple(body['box'])!=tuple(self.active_box or ()):response=self.answer(raw,6,dict(x=x+w//2,y=y+h//2),'select_body_for_contact_experiment',body,path)
        else:response=self.answer(raw,path[0],{},'approach_unknown_body_interaction' if len(path)>1 else 'test_unknown_body_interaction',body,path)
        if not response['done']:response['certificate']['contact_experiment']=dict(target=copy.deepcopy(other),planned_controls=path,interaction_is_hypothesis=True,purpose='test_unknown_object_interaction_after_known_plans_fail')
        return response
