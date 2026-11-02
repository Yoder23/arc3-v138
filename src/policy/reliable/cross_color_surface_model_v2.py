"""Recognize observed color pads and form explicit contact-avoidance hypotheses."""
from collections import Counter
from structured_interaction_probe_v1 import parts
from cross_shape_geometry_v2 import shape_points

def sites(obs):
    f=obs['frame'];bg=Counter(v for row in f for v in row).most_common(1)[0][0];out=[]
    for q in parts(f):
        if q['h']!=q['w'] or not(3<=q['h']<=8) or q['area']!=q['h']**2:continue
        y,x,s=q['y'],q['x'],q['h'];ring={(y-1,b) for b in range(x-1,x+s+1)}|{(y+s,b) for b in range(x-1,x+s+1)}|{(a,x-1) for a in range(y,y+s)}|{(a,x+s) for a in range(y,y+s)}
        values={f[a][b] for a,b in ring if 0<=a<64 and 0<=b<64}
        if len(values)==1 and bg not in values and q['color'] not in values:out.append(dict(color=q['color'],y=y,x=x,size=s))
    return out

def safe(center,geometry,color,pads,margin=0):
    pts=shape_points(center,geometry)
    return not any(p['color']!=color and any((y,x) in pts for y in range(p['y']-margin,p['y']+p['size']+margin) for x in range(p['x']-margin,p['x']+p['size']+margin)) for p in pads)

def infer_margin(center,geometry,color,pads):
    matching=[p for p in pads if p['color']==color]
    if len(matching)!=1:return None
    p=matching[0];pts=shape_points(center,geometry)
    for margin in range(4):
        if pts&{(y,x) for y in range(p['y']-margin,p['y']+p['size']+margin) for x in range(p['x']-margin,p['x']+p['size']+margin)}:return p,margin
    return None
