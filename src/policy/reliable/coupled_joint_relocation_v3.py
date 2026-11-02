"""Bounded planning through intermediate actor movements and selected-obstacle relocations."""
import heapq,itertools,math
from collections import deque
from coupled_navigation_core_v9 import cells

def search(obs,m,floor,effects,limit=120000):
    hazards=set(m.get('hazard_colors',[]));size=m['signature'][1];shape=tuple(map(tuple,m['shape']));start=(tuple(map(tuple,m['actor_positions'])),tuple(m['origin']),1);f=[row[:] for row in obs['frame']]
    for y,x in cells(start[0],size):f[y][x]=floor
    for dy,dx in shape:f[start[1][0]+dy][start[1][1]+dx]=floor
    pressure=m.get('pressure_surface',{});pressure_roles={r['color']:r for r in pressure.get('roles',[])};pressure_models={r['color']:r for r in pressure.get('models',[])};gated={}
    for color,r in pressure_roles.items():
        for y,x in r['buttons']:
            for dy in range(size):
                for dx in range(size):f[y+dy][x+dx]=floor
        if color in pressure_models:
            for point in pressure_models[color]['gates']:gated[tuple(point)]=color
    def surface(point,pair):
        y,x=point;color=gated.get(point)
        if color is not None:return floor if any(tuple(p) in pair for p in pressure_roles[color]['buttons']) else color
        return f[y][x]
    object_effects={a:tuple(delta[0]) for a,delta in effects.items() if a in (1,2,3,4,7)}
    for a,deltas in m['models'].items():
        if len(deltas)==1:object_effects[a]=next(iter(deltas))
    actor_foot={};marker_foot={};motion_cache={};object_cache={}
    def footprint(pos):
        if pos not in actor_foot:actor_foot[pos]=frozenset((pos[0]+a,pos[1]+b) for a in range(size) for b in range(size))
        return actor_foot[pos]
    def marked(pos):
        if pos not in marker_foot:marker_foot[pos]=frozenset((pos[0]+a,pos[1]+b) for a,b in shape)
        return marker_foot[pos]
    def free(points,pair):return all(0<y<63 and 0<x<63 and surface((y,x),pair)==floor for y,x in points)
    def actor_moves(pair):
        if pair not in motion_cache:
            options=[]
            for a,deltas in sorted(effects.items()):
                out=[];unsafe=False
                for pos,(dy,dx) in zip(pair,deltas):
                    nxt=(pos[0]+dy,pos[1]+dx);unsafe|=any(0<=y<64 and 0<=x<64 and f[y][x] in hazards for y,x in footprint(nxt));out.append(nxt if free(footprint(nxt),pair) else pos)
                if not unsafe:options.append((a,tuple(out)))
            motion_cache[pair]=options
        return motion_cache[pair]
    def object_moves(pos,pair):
        key=(pos,pair)
        if key not in object_cache:
            object_cache[key]=[(a,(pos[0]+dy,pos[1]+dx)) for a,(dy,dx) in sorted(object_effects.items()) if free(marked((pos[0]+dy,pos[1]+dx)),pair) and (pos,a) not in m['failures']]
        return object_cache[key]
    max_step=max((abs(dy)+abs(dx) for pair in effects.values() for dy,dx in pair),default=1)
    def h(state):
        a,b=state[0];return math.ceil((abs(a[0]-b[0])+abs(a[1]-b[1]))/(2*max_step))
    serial=itertools.count();q=[(3*h(start),0,next(serial),start)];best={start:0};parents={};expanded=0;goal=None
    while q and expanded<limit:
        _,g,_,state=heapq.heappop(q)
        if g!=best[state]:continue
        expanded+=1;pair,marker,mode=state
        if pair[0]==pair[1]:goal=state;break
        successors=[((pair,marker,1-mode),('select_object' if mode==0 else 'select_actors',6))]
        if mode==0:
            for action,out in actor_moves(pair):
                after=tuple(a if footprint(b)&marked(marker) else b for a,b in zip(pair,out))
                if after!=pair:successors.append(((after,marker,0),('move_actors',action)))
        else:
            occupied=footprint(pair[0])|footprint(pair[1])
            for action,nxt in object_moves(marker,pair):
                if not marked(nxt)&occupied:successors.append(((pair,nxt,1),('move_object',action)))
        for nxt,action in successors:
            cost=g+1
            if cost<best.get(nxt,10**9):best[nxt]=cost;parents[nxt]=(state,action);heapq.heappush(q,(cost+3*h(nxt),cost,next(serial),nxt))
    if goal is None:return None,dict(expanded=expanded,states=len(best),joint_plan_is_hypothesis=True)
    path=[];here=goal
    while here!=start:
        before,action=parents[here];kind,button=action;data={}
        if kind=='select_actors':y,x=before[0][0];data=dict(y=y+size//2,x=x+size//2)
        elif kind=='select_object':dy,dx=shape[0];data=dict(y=before[1][0]+dy,x=before[1][1]+dx)
        path.append(dict(kind=kind,action=button,data=data,positions=here[0],marker=here[1],mode=here[2]));here=before
    return list(reversed(path)),dict(expanded=expanded,states=len(best),joint_plan_is_hypothesis=True,object_control_transfer_is_hypothesis=True)
