"""Normalize self occlusion in failure memory and apply learned contexts during routing."""
import copy
from collections import deque
from selectable_multi_object_learner_v18 import Agent as Base
from selectable_rect_core_v1 import inside,same
class Agent(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.floor_witness=None
    def reset_level(self,raw):super().reset_level(raw);self.floor_witness=None
    def observe(self,raw):
        n=len(self.motion_memory);r=super().observe(raw)
        if len(self.motion_memory)>n:
            m=self.motion_memory[-1];self.floor_witness=dict(source=m['source'],before=copy.deepcopy(m['before']),after=copy.deepcopy(m['after']),color=self.floor,hypothesis='vacated_body_pixels_are_a_terrain_fill_hypothesis')
        return r
    def context(self,raw,dest,objects,body):
        y,x=dest;h,w=body['box'][2:]
        values=[self.floor if self.floor is not None and inside((a,b),body['box']) else raw['frame'][a][b] if 0<=a<64 and 0<=b<64 else -1 for a in range(y,y+h) for b in range(x,x+w)]
        return (tuple(values),tuple(sorted(tuple(q['box']) for q in objects if not same(q,body))))
    def answer(self,*args,**kwargs):
        r=super().answer(*args,**kwargs)
        if not r['done']:r['certificate']['floor_hypothesis']=copy.deepcopy(self.floor_witness)
        return r
    def route(self,raw,body,goal):
        start=tuple(body['box'][:2]);target=(goal['box'][0]+1,goal['box'][1]+1);h,w=body['box'][2:];others=[q for q in self.objects if not same(q,body)];allowed={self.floor}|{g['ink'] for g in self.goals}|self.extra_terrain
        todo=deque([start]);parents={start:None}
        while todo:
            at=todo.popleft()
            if at==target:
                route=[]
                while parents[at] is not None:prev,a=parents[at];route.append(a);at=prev
                return route[::-1]
            for a,m in sorted(self.motions.items()):
                dy,dx=m['delta'];q=(at[0]+dy,at[1]+dx)
                if q in parents or not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
                if any(inside((y,x),o['box']) for y in range(q[0],q[0]+h) for x in range(q[1],q[1]+w) for o in others):continue
                if any(not inside((y,x),body['box']) and raw['frame'][y][x] not in allowed for y in range(q[0],q[0]+h) for x in range(q[1],q[1]+w)):continue
                context=self.context(raw,q,self.objects,body)
                if any(f['action']==a and tuple(f['body']['box'][:2])==at and f['context']==context for f in self.failures):continue
                ident=self.identities.get(tuple(body['box']))
                if any(c['identity']==ident and tuple(c['delta'])==tuple(m['delta']) and tuple(c['pattern'])==tuple(context[0]) for c in self.constraint_hypotheses):continue
                parents[q]=(at,a);todo.append(q)
        return None
