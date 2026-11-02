"""Hypothesis: forward sight activates pursuit of the previously observed actor."""
from collections import deque
def advance(actor,heading,pos,links,stride,radius,active):
    dy,dx=heading;delta=actor[0]-pos[0],actor[1]-pos[1];distance=delta[0]*dy+delta[1]*dx
    sight=((dy==0 and delta[0]==0)or(dx==0 and delta[1]==0))and 0<distance<=stride*radius and distance%stride==0
    if not(active or sight):return heading,pos
    queue=deque([(pos,[])]);seen={pos};path=None
    while queue:
        at,route=queue.popleft()
        if at==actor:path=route;break
        for a,q in sorted(links.get(at,{}).items()):
            if q not in seen:seen.add(q);queue.append((q,route+[q]))
    if not path:return heading,pos
    pos=path[0]
    if len(path)>1:heading=tuple((b-a)//stride for a,b in zip(pos,path[1]))
    return heading,pos
