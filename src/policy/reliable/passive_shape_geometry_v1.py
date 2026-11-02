"""Literal connected components and enclosed outline interiors, without role labels."""
from collections import deque
from visible_passive_components_v1 import components

def enclosed(component):
    y,x,h,w=component['box'];wall=set(map(tuple,component['shape']));outside=set();todo=deque()
    for a in range(h):
        for b in range(w):
            if (a in (0,h-1) or b in (0,w-1)) and (a,b) not in wall:outside.add((a,b));todo.append((a,b))
    while todo:
        a,b=todo.popleft()
        for p in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
            if 0<=p[0]<h and 0<=p[1]<w and p not in wall and p not in outside:outside.add(p);todo.append(p)
    inside={(a,b) for a in range(h) for b in range(w)}-wall-outside
    if not inside:return None
    ay=min(a for a,b in inside);ax=min(b for a,b in inside);by=max(a for a,b in inside);bx=max(b for a,b in inside)
    return dict(box=(y+ay,x+ax,by-ay+1,bx-ax+1),shape=tuple(sorted((a-ay,b-ax) for a,b in inside)))

def mask(pos,shape):
    return sum(1<<((pos[0]+a)*64+pos[1]+b) for a,b in shape)
