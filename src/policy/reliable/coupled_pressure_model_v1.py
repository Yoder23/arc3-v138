"""Infer pressure-controlled surfaces from observed occupancy and remote color changes."""
from collections import defaultdict,deque
import copy
from structured_interaction_probe_v1 import parts
from coupled_navigation_core_v10 import actors,cells,board
from visual_transform_learner import digest

def roles(obs,size,floor,actor_color):
    groups=defaultdict(lambda:dict(buttons=[],gates=[]))
    for q in parts(obs['frame']):
        if q['color'] in (floor,actor_color) or q['area']!=q['h']*q['w']:continue
        if q['h']==q['w']==size:groups[q['color']]['buttons'].append((q['y'],q['x']))
        elif (q['h']==size and q['w']>size and q['w']%size==0) or (q['w']==size and q['h']>size and q['h']%size==0):groups[q['color']]['gates'].extend((q['y']+y,q['x']+x) for y,x in q['shape'])
    return {c:dict(color=c,buttons=sorted(v['buttons']),gates=sorted(v['gates']),source=digest(obs),interpretation='equal_tile_and_wide_bar_same_color') for c,v in groups.items() if v['buttons'] and v['gates']}

def search(obs,pos,size,floor,effects,role_memory,models,hazards):
    f=board(obs,pos,size,floor);known=list(role_memory.values());button_cells=set();gated={};unknown=[]
    for r in known:
        for button in r['buttons']:button_cells.update(cells([button],size))
        if r['color'] in models:
            for p in models[r['color']]['gates']:gated[tuple(p)]=r['color']
        else:unknown.extend((r['color'],tuple(p)) for p in r['buttons'])
    for y,x in button_cells:f[y][x]=floor
    def predict(here,deltas):
        active={r['color'] for r in known if r['color'] in models and any(tuple(p) in here for p in r['buttons'])};result=[]
        for (y,x),(dy,dx) in zip(here,deltas):
            ny,nx=y+dy,x+dx;points=cells([(ny,nx)],size)
            if any(0<=a<64 and 0<=b<64 and f[a][b] in hazards for a,b in points):return None
            def surface(a,b):
                c=gated.get((a,b));return floor if c is not None and c in active else c if c is not None else f[a][b]
            good=all(0<a<63 and 0<b<63 and surface(a,b)==floor for a,b in points);result.append((ny,nx) if good else (y,x))
        return tuple(result)
    queue=deque([(pos,[])]);seen={pos};probe=None
    while queue and len(seen)<25000:
        here,path=queue.popleft()
        if path and here[0]==here[1]:return path,dict(kind='coincident_actors',expanded=len(seen))
        if path and probe is None:
            target=next(((c,b) for c,b in unknown if b in here),None)
            if target:probe=(path,dict(kind='test_unmodeled_pressure_tile',color=target[0],button=target[1]))
        for action,delta in sorted(effects.items()):
            after=predict(here,delta)
            if after is not None and after not in seen:seen.add(after);queue.append((after,path+[(action,after)]))
    if probe:return probe[0],dict(**probe[1],expanded=len(seen))
    return None,dict(kind='unreachable_under_current_surface_hypotheses',expanded=len(seen))
