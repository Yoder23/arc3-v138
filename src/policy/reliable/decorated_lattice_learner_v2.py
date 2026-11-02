"""Acquire visible one-to-many click effects and compose plans for structured cells."""
from collections import defaultdict,deque
import copy
import numpy as np
from partial_nested_learner import Learner as Prior
from partial_nested_perception import expanded
from unknown_lattice_inquiry_v1 import hypotheses
from visual_transform_learner import public,digest


from coupled_lattice_learner_v1 import layout as original_layout
from decorated_lattice_perception_v2 import layout as decorated_layout
def layout(frame,memory):
    return decorated_layout(frame,memory) or original_layout(frame,memory)


def read_variables(frame,scene):
    values={};s=scene['size']
    for v in scene['variables']:
        y,x=v['y'],v['x'];observed=set()
        for dy in range(s):
            for dx in range(s):
                color=frame[y+dy][x+dx]
                if v['mask'][dy][dx]:observed.add(color)
                elif color!=v['fixed'][dy][dx]:return None
        if len(observed)!=1:return None
        values[y,x]=observed.pop()
    return values


def action_models(effects,level,palette):
    by=defaultdict(list)
    for e in effects:
        if e['level']==level:by[tuple(e['point'])].append(e)
    out={}
    for point,rows in sorted(by.items()):
        footprints={tuple(tuple(c[:2]) for c in e['changes']) for e in rows}
        if len(footprints)!=1:continue
        footprint=next(iter(footprints))
        if not footprint or point not in footprint:continue
        transitions={p:{} for p in footprint};consistent=True
        for e in rows:
            for y,x,a,b in e['changes']:
                d=transitions[y,x]
                if a in d and d[a]!=b:consistent=False
                d[a]=b
        if not consistent:continue
        ready=all(set(d)==set(palette) and set(d.values())==set(palette) for d in transitions.values())
        out[point]=dict(ready=ready,support=[e['row'] for e in rows],transitions=transitions)
    return out


class Learner(Prior):
    def __init__(self):
        super().__init__();self.effects=[]

    def observe(self,raw,last=None,data=None):
        obs=public(raw);before=self.previous
        super().observe(obs,last,data)
        if before is None or last!=6 or before['state']!=obs['state'] or obs['state']!='NOT_FINISHED' or before['levels_completed']!=obs['levels_completed']:return
        p=layout(before['frame'],self.memory)
        if not p:return
        old=read_variables(before['frame'],p);new=read_variables(obs['frame'],p)
        if old is None or new is None:return
        s=p['size'];hits=[(v['y'],v['x']) for v in p['variables'] if v['y']<=data['y']<v['y']+s and v['x']<=data['x']<v['x']+s]
        if len(hits)!=1:return
        self.effects.append(dict(row=len(self.rows)-1,level=obs['levels_completed'],point=hits[0],
            changes=[(y,x,old[y,x],new[y,x]) for y,x in sorted(old) if old[y,x]!=new[y,x]]))

    def propose(self,raw):
        obs=public(raw)
        if obs['state']!='NOT_FINISHED' or 6 not in obs['available_actions']:return super().propose(obs)
        scene=layout(obs['frame'],self.memory)
        if not scene:return super().propose(obs)
        current=read_variables(obs['frame'],scene);structured=sorted((v['y'],v['x']) for v in scene['variables'] if v['structured'])
        models=action_models(self.effects,obs['levels_completed'],scene['palette']);allowed={}
        for c in scene['constraints']:
            allowed[c['y'],c['x']]=[v for v in scene['palette'] if (not c['equal'] or v in c['equal']) and v not in c['unequal']]
        def certificate(point,phase,plan=()):
            y,x=point;m=models.get(point);support=m['support'] if m else []
            forecast=[]
            if m:
                for (yy,xx),transitions in m['transitions'].items():
                    if current[yy,xx] in transitions:forecast.append((yy,xx,transitions[current[yy,xx]]))
            return dict(kind=('decorated_lattice' if 'decorations' in scene else 'coupled_lattice'),phase=phase,action=6,data=dict(x=x+scene['size']//2,y=y+scene['size']//2),
                box=(y,x,scene['size'],scene['size']),scene=copy.deepcopy(scene),support=support,
                evidence=[copy.deepcopy(e) for e in self.effects if e['row'] in support],forecast=forecast,plan=list(plan),
                scope='Tentative structured states and observed context-specific effect cycles. Goals inherit only demonstrated local relations; replan after each actual outcome.')
        for point in structured:
            trials=[e for e in self.effects if e['level']==obs['levels_completed'] and tuple(e['point'])==point]
            if (point not in models or not models[point]['ready']) and len(trials)<len(scene['palette'])+1:
                return certificate(point,'acquire')
        # A demonstrated one-variable cycle can satisfy its own constraint
        # without enumerating an exponential product of independent cells.
        if 'decorations' in scene:
            for point,m in sorted(models.items()):
                if not m['ready'] or set(m['transitions'])!={point} or point not in allowed:continue
                value=current[point]
                if value in allowed[point]:continue
                path=[]
                for _ in scene['palette']:
                    value=m['transitions'][point][value];path.append(point)
                    if value in allowed[point]:return certificate(point,'plan',path)
        start=tuple(current[p] for p in structured)
        def solved(state):return all(v in allowed.get(p,scene['palette']) for p,v in zip(structured,state))
        if not solved(start):
            todo=deque([(start,())]);seen={start}
            while todo and len(seen)<=4096:
                state,path=todo.popleft()
                if solved(state) and path:return certificate(path[0],'plan',path)
                for point,m in sorted(models.items()):
                    if not m['ready']:continue
                    next_state=tuple(m['transitions'].get(p,{}).get(v,v) for p,v in zip(structured,state))
                    if next_state not in seen:seen.add(next_state);todo.append((next_state,path+(point,)))
        for point,legal in sorted(allowed.items()):
            if point not in structured and current[point] not in legal:
                return certificate(point,'repair')
        return super().propose(obs)

    def commit(self,c):
        if c['kind'] in ('coupled_lattice','decorated_lattice'):
            y,x,_,_=c['box'];self.visits[self.level,y,x]+=1
        else:super().commit(c)
