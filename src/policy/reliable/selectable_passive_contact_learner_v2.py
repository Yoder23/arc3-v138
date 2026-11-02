"""Retain source-grounded terrain observations across a contact approach."""
import copy
from collections import Counter,deque
from selectable_passive_contact_learner_v1 import Agent as Base
from selectable_rect_core_v1 import inside
from visible_passive_components_v1 import components
class Agent(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.passive_terrain_memory={}
    def reset_level(self,raw):super().reset_level(raw);self.passive_terrain_memory={}
    def observe(self,raw):
        r=super().observe(raw)
        if self.floor_witness:self.passive_terrain_memory.setdefault(self.floor_witness['color'],copy.deepcopy(self.floor_witness))
        return r
    def candidates(self,raw):
        bg=Counter(raw['frame'][y][x] for y,x in ((0,0),(0,63),(63,0),(63,63))).most_common(1)[0][0];excluded={bg,self.palette,self.floor}|set(self.passive_terrain_memory)|{g['ink'] for g in self.goals}
        return [q for q in components(raw['frame']) if q['ink'] not in excluded and 4<=len(q['shape'])<=144 and 0<q['box'][0] and 0<q['box'][1] and q['box'][0]+q['box'][2]<64 and q['box'][1]+q['box'][3]<64]
    def contact_route(self,raw,body,target):
        cells={(target['box'][0]+y,target['box'][1]+x) for y,x in target['shape']};h,w=body['box'][2:];start=tuple(body['box'][:2]);todo=deque([start]);parents={start:None};allowed=set(self.passive_terrain_memory)|{self.floor}|{g['ink'] for g in self.goals}
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
    def answer(self,*args,**kwargs):
        r=super().answer(*args,**kwargs)
        if not r['done']:r['certificate']['passive_terrain_memory']=copy.deepcopy(list(self.passive_terrain_memory.values()))
        return r
