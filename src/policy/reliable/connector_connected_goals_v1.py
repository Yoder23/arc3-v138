"""Enumerate geometric alternatives for action-feasible assembly selection."""
from collections import Counter
from connector_assembly_geometry_v1 import marker_sets,patches,rotate,valid,complete

def connected(pieces):
    if not valid(pieces) or not pieces:return False
    reached={0}
    while True:
        new={j for i in reached for j in range(len(pieces)) if set(marker_sets(pieces[i]))&set(marker_sets(pieces[j]))}
        if new<=reached:break
        reached|=new
    return len(reached)==len(pieces)

def solve_connected(pieces,limit=12000):
    if len(pieces)>7:return [],dict(nodes=0,reason='piece_limit')
    anchor=max(range(len(pieces)),key=lambda i:len(pieces[i]['shape']));nodes=0;solutions=[];seen=set()
    def search(placed):
        nonlocal nodes
        nodes+=1
        if nodes>limit or len(solutions)>=48:return
        key=tuple(sorted((i,o['shape'],o['origin']) for i,o in placed.items()))
        if key in seen:return
        seen.add(key)
        if len(placed)==len(pieces):
            if connected(list(placed.values())):solutions.append(placed.copy())
            return
        counts=Counter(p for o in placed.values() for p in marker_sets(o));opens=[p for p,n in counts.items() if n==1]
        if not opens:return
        alternatives=[]
        for slot in opens:
            sy=min(y for y,x in slot);sx=min(x for y,x in slot);signature={(y-sy,x-sx) for y,x in slot};choices=[];dedup=set()
            for i,piece in enumerate(pieces):
                if i in placed:continue
                for turn in range(4):
                    shape=rotate(piece['shape'],turn)
                    for norm,offset,cells in patches(shape,2):
                        if set(norm)!=signature:continue
                        origin=sy-offset[0],sx-offset[1];k=i,shape,origin
                        if k in dedup:continue
                        dedup.add(k);candidate=dict(piece,shape=shape,origin=origin)
                        if valid(list(placed.values())+[candidate]):choices.append((i,candidate))
            alternatives.append(choices)
        for i,obj in sorted({(i,o['shape'],o['origin']):(i,o) for choices in alternatives for i,o in choices}.values(),key=lambda q:(abs(q[1]['origin'][0]-pieces[q[0]]['origin'][0])+abs(q[1]['origin'][1]-pieces[q[0]]['origin'][1]),q[0],q[1]['origin'])):
            placed[i]=obj;search(placed);del placed[i]
    search({anchor:pieces[anchor]})
    def cost(solution):return sum(abs(o['origin'][0]-pieces[i]['origin'][0])+abs(o['origin'][1]-pieces[i]['origin'][1])+6*(o['shape']!=pieces[i]['shape']) for i,o in solution.items())
    best=min(solutions,key=cost) if solutions else None
    return sorted(solutions,key=cost),dict(nodes=nodes,solutions=len(solutions),anchor=anchor,goal_is_hypothesis=True)
