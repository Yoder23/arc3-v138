"""Tentative small outlined objects from literal borders, without game identifiers."""
from collections import defaultdict

def rings(frame):
    out=[]
    for n in (3,5,7):
        for y in range(65-n):
            for x in range(65-n):
                ink=frame[y][x]
                if frame[y+n//2][x+n//2]==ink:continue
                if all(frame[y][b]==frame[y+n-1][b]==ink for b in range(x,x+n)) and all(frame[a][x]==frame[a][x+n-1]==ink for a in range(y,y+n)):
                    out.append(dict(box=(y,x,n,n),ink=ink,center=frame[y+n//2][x+n//2]))
    return out

def actor_group(frame):
    groups=defaultdict(list)
    for ring in rings(frame):groups[ring['box'][2],ring['ink']].append(ring)
    choices=[(size,ink,rs) for (size,ink),rs in groups.items() if 2<=len(rs)<=4]
    return min(choices,key=lambda p:(p[0],p[1]))[2] if choices else []
