"""Acquire visible one-to-many click effects and compose plans for structured cells."""
from collections import defaultdict,deque
import copy
import numpy as np
from partial_nested_learner import Learner as Prior
from partial_nested_perception import expanded
from unknown_lattice_inquiry_v1 import hypotheses
from visual_transform_learner import public,digest


def layout(frame,memory):
    scenes=expanded(frame,memory)
    if not scenes:return None
    p=scenes[0];size=p['size'];sy,sx=p['pitch'];oy,ox=p['cells'][0][0]%sy,p['cells'][0][1]%sx
    controls=hypotheses(frame,memory)
    controls=[c for c in controls if c['box'][2]==size and tuple(c['pitch'])==(sy,sx)]
    if not controls:return None
    palette=sorted({v for y,x,v in p['cells']}|{q['pattern'][1][1] for q in p['markers']})
    a=np.asarray(frame);variables={};structured={tuple(c['box'][:2]) for c in controls}
    for y in range(oy,len(a)-size+1,sy):
        for x in range(ox,a.shape[1]-size+1,sx):
            patch=a[y:y+size,x:x+size];v=int(patch[size//2,size//2])
            if v not in palette:continue
            uniform=bool(np.all(patch==v))
            if not uniform and (y,x) not in structured:continue
            mask=patch==v
            variables[y,x]=dict(value=v,mask=mask.tolist(),fixed=np.where(mask,-1,patch).tolist(),structured=not uniform)
    con=defaultdict(lambda:dict(equal=set(),unequal=set()))
    ink,flip,turn=p['memory']['rule']
    for m in p['markers']:
        y,x,_,_=m['box'];q=np.asarray(m['pattern']);q=np.rot90(np.fliplr(q) if flip else q,turn)
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if not(dy or dx):continue
                pos=y+dy*sy,x+dx*sx;v=int(q[dy+1,dx+1])
                if pos in variables and v in p['inks']:con[pos]['equal' if v==ink else 'unequal'].add(int(q[1,1]))
    if any(len(c['equal'])>1 or c['equal']&c['unequal'] for c in con.values()):return None
    return dict(size=size,pitch=(sy,sx),palette=palette,
        variables=[dict(y=y,x=x,**v) for (y,x),v in sorted(variables.items())],
        constraints=[dict(y=y,x=x,equal=sorted(c['equal']),unequal=sorted(c['unequal'])) for (y,x),c in sorted(con.items())],
        source=p['memory']['source'],examples=copy.deepcopy(p['memory']['examples']),rule=p['memory']['rule'],
        anchor=p['anchor'],markers=p['markers'],inks=p['inks'],background=p['background'])


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
            return dict(kind='coupled_lattice',phase=phase,action=6,data=dict(x=x+scene['size']//2,y=y+scene['size']//2),
                box=(y,x,scene['size'],scene['size']),scene=copy.deepcopy(scene),support=support,
                evidence=[copy.deepcopy(e) for e in self.effects if e['row'] in support],forecast=forecast,plan=list(plan),
                scope='Tentative structured states and observed context-specific effect cycles. Goals inherit only demonstrated local relations; replan after each actual outcome.')
        for point in structured:
            trials=[e for e in self.effects if e['level']==obs['levels_completed'] and tuple(e['point'])==point]
            if (point not in models or not models[point]['ready']) and len(trials)<len(scene['palette'])+1:
                return certificate(point,'acquire')
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
        if c['kind']=='coupled_lattice':
            y,x,_,_=c['box'];self.visits[self.level,y,x]+=1
        else:super().commit(c)
