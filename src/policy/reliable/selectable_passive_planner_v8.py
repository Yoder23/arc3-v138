"""After an unchanged contact, retain the attempt and approach a different contact face."""
import copy
from collections import deque
from selectable_passive_planner_v7 import Agent as Base
from selectable_rect_core_v1 import inside
class Agent(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.passive_contact_failures={};self.passive_level_source=0
    def reset_level(self,raw):super().reset_level(raw);self.passive_contact_failures={};self.passive_level_source=self.t
    def contact_route(self,raw,body,target):
        cells={(target['box'][0]+y,target['box'][1]+x) for y,x in target['shape']};h,w=body['box'][2:];start=tuple(body['box'][:2]);todo=deque([start]);parents={start:None};allowed=set(self.passive_terrain_memory)|{self.floor}|{g['ink'] for g in self.goals}
        while todo:
            at=todo.popleft()
            for a,m in sorted(self.motions.items()):
                dy,dx=m['delta'];q=(at[0]+dy,at[1]+dx)
                if not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
                pixels={(y,x) for y in range(q[0],q[0]+h) for x in range(q[1],q[1]+w)}
                if pixels&cells and (tuple(at),tuple(target['box']),a) not in self.passive_contact_failures:
                    path=[a];cursor=at
                    while parents[cursor] is not None:prev,act=parents[cursor];path.append(act);cursor=prev
                    return path[::-1]
                if q in parents or any(not inside((y,x),body['box']) and raw['frame'][y][x] not in allowed for y,x in pixels):continue
                parents[q]=(at,a);todo.append(q)
        return None

    def respond(self,raw):
        r=super().respond(raw)
        for _ in range(8):
            if not r['done'] or raw['state']!='NOT_FINISHED' or self.passive_planning or len(self.passive_contact_failures)>=8:return r
            state=self.passive_probe_state
            if not state or not state.get('contact') or not state['contact'].get('processed'):return r
            p=state['contact'];key=(tuple(p['actor']['box'][:2]),tuple(p['target']['box']),p['action'])
            if key in self.passive_contact_failures:return r
            target=p['target'];y,x,h,w=target['box']
            if not all(raw['frame'][y+a][x+b]==target['ink'] for a,b in target['shape']):return r
            if not any(tuple(b['box'])==tuple(p['actor']['box']) for b in self.objects):return r
            self.passive_contact_failures[key]=copy.deepcopy(p);self.passive_probe_state=None;r=super().respond(raw)
        return r
    def answer(self,*args,**kwargs):
        r=super().answer(*args,**kwargs)
        if not r['done']:r['certificate']['failed_passive_contacts']=copy.deepcopy(list(self.passive_contact_failures.values()))
        return r
