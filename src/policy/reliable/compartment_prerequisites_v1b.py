"""Propose bounded fill interventions at visible gaps across disconnected effects."""
import math
def proposals(s,g,models,trials):
    goal={i for i,t in enumerate(g['targets'])if t is not None};reachable=set(goal)
    changed=True
    while changed:
        changed=False
        for d in models.values():
            indices={i for i,v in enumerate(d)if v}
            if indices&reachable and not indices<=reachable:reachable|=indices;changed=True
    steps=[abs(v)for d in models.values()for v in d if v];step=math.gcd(*steps)if steps else 0
    if not step:return []
    axis=g['axis'];orth=1-axis;out=[]
    for b in s['buttons']:
        box=b['box']
        if box[axis+2]<=box[orth+2]:continue
        left=[i for i,z in enumerate(g['segments'])if 0<=box[orth]-z['span'][1]<=box[orth+2]]
        right=[i for i,z in enumerate(g['segments'])if 0<=z['span'][0]-box[orth]-box[orth+2]<=box[orth+2]]
        if len(left)!=1 or len(right)!=1:continue
        a,c=left[0],right[0]
        if (a in reachable)==(c in reachable):continue
        dest=c if a in reachable else a;z=g['segments'][dest]
        candidates=[box[axis]+box[axis+2]-step,box[axis],box[axis]-step]if z['side']=='min'else[box[axis]+step,box[axis]+box[axis+2],box[axis]+box[axis+2]+step]
        for v in candidates:
            if not z['bounds'][0]<=v<=z['bounds'][1]or(dest,v)in trials:continue
            if (v-s['positions'][dest])%step:continue
            target=[None]*len(s['positions']);target[dest]=v
            out.append(dict(index=dest,target=v,targets=target,aperture=b,reason='Unmarked capacity may connect currently disconnected observed control effects; geometric hypothesis, not confirmed causality.'))
    return out
