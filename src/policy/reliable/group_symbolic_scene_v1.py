"""Interpret compound visual goal labels as observed sets of symbols."""
from collections import Counter
from structured_interaction_probe_v1 import parts
from group_centroid_learner_v13 import scene as single_scene
from visual_transform_learner import digest
DISK=[(dy,dx) for dy in range(-2,3) for dx in range(-2,3) if (dy or dx) and not(abs(dy)==abs(dx)==2)]
RING=[(dy,dx) for dy in [-3,-2,-1,1,2,3] for dx in [-3,-2,-1,1,2,3] if abs(dy)+abs(dx)==4]

def scene(obs):
    old=single_scene(obs);f=obs['frame'];bg=Counter(v for row in f for v in row).most_common(1)[0][0];ends=[]
    for p in parts(f):
        if p['h']==p['w']==5 and p['area']==12:
            y,x=p['y']+2,p['x']+2;ends.append(dict(color=p['color'],point=(y,x),group=f[y][x]))
    centers={};signatures={}
    for g in sorted({p['group'] for p in ends}):
        members=[p for p in ends if p['group']==g]
        if len(members)<2:continue
        y,x=tuple(sum(p['point'][i] for p in members)//len(members) for i in (0,1));values={f[y+dy][x+dx] for dy,dx in DISK}
        if bg not in values and g in values and f[y][x] not in values:centers[g]=(y,x);signatures[g]=values
    if not any(len(v)>1 for v in signatures.values()):return old
    rings=[]
    for y in range(3,61):
        for x in range(3,61):
            if f[y][x]!=bg:continue
            vals=[f[y+dy][x+dx] for dy,dx in RING]
            if bg in vals:continue
            if any(f[y+dy][x+dx]!=bg for dy in range(-3,4) for dx in range(-3,4) if (dy,dx) not in RING):continue
            rings.append(dict(center=(y,x),points=[(y+dy,x+dx) for dy,dx in RING],point_colors=vals,signature=sorted(set(vals))))
    goals=[]
    for g,signature in signatures.items():
        options=[r for r in rings if set(r['signature'])<=signature]
        if options:
            chosen=min(options,key=lambda r:(-len(r['signature']),abs(r['center'][0]-centers[g][0])+abs(r['center'][1]-centers[g][1]),r['center']))
            goals.append(dict(chosen,color=g,marker_signature=sorted(signature),marker_center=centers[g],signature_source=digest(obs),interpretation='goal_symbol_subset_hypothesis'))
    return sorted(ends,key=lambda p:(p['group'],p['point'])),centers,goals
