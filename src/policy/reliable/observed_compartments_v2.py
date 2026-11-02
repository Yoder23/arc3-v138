"""Visible compartment boundaries, including unmarked prerequisite variables."""
from collections import Counter
from binary_demonstration_bootstrap_v1 import components

def discover(frame,s):
    axes={p['axis']for p in s['pairs']}
    if len(axes)!=1:return None
    axis=next(iter(axes));orth=1-axis;obs=components(frame);options=[]
    for p in s['pairs']:
        box=p['actor']['box'];at=[box[0]+box[2]//2,box[1]+box[3]//2]
        for sign in [-1,1]:
            v=list(at);v[axis]=box[axis]-1 if sign<0 else box[axis]+box[axis+2]
            if not all(0<=q<64 for q in v):continue
            ink=frame[v[0]][v[1]]
            for o in obs:
                y,x,h,w=o['box']
                if o['ink']==ink and(y<=v[0]<y+h and x<=v[1]<x+w)and(v[0]-y,v[1]-x)in o['shape']:
                    density=len(o['shape'])/(h*w)
                    if density>=.75 and 8<=len(o['shape'])<2048:options.append((density,-len(o['shape']),ink,sign))
    if not options:return None
    _,_,ink,sign=max(options)
    regions=[o for o in obs if o['ink']==ink and o['box'][orth+2]>=4 and len(o['shape'])>=8]
    regions.sort(key=lambda o:o['box'][orth]);segments=[]
    for o in regions:
        box=o['box'];sample=box[orth]+box[orth+2]//2
        overlays=[p['actor']['box']for p in s['pairs']]+[b['box']for b in s['buttons']]
        clear=[q for q in range(box[orth],box[orth]+box[orth+2])if not any(b[orth]<=q<b[orth]+b[orth+2]for b in overlays)]
        if clear:sample=min(clear,key=lambda q:abs(q-sample))
        line=[frame[sample][q]if axis==1 else frame[q][sample]for q in range(64)]
        values=[q for q,v in enumerate(line)if v==ink and box[axis]<=q<box[axis]+box[axis+2]]
        if not values:continue
        side='min'if sign>0 else'max';boundary=min(values)if side=='min'else max(values)+1
        far=max(values)+1 if side=='min'else min(values)
        # Bounds follow the contiguous two-color region adjacent to the interface.
        near=boundary-1 if side=='min'else boundary
        background=line[near]if 0<=near<64 else None
        allowed={ink,background};lo=min(values);hi=max(values)+1
        while lo>0 and line[lo-1]in allowed:lo-=1
        while hi<64 and line[hi]in allowed:hi+=1
        segments.append(dict(sample=sample,span=(box[orth],box[orth]+box[orth+2]),side=side,far=far,bounds=(lo,hi),initial=boundary))
    targets=[None]*len(segments);bindings=[]
    for p in s['pairs']:
        at=p['actor']['box'][orth]+p['actor']['box'][orth+2]/2
        hits=[i for i,z in enumerate(segments)if z['span'][0]<=at<z['span'][1] and z['bounds'][0]<=p['current']<=z['bounds'][1]]
        if len(hits)!=1:return None
        i=hits[0];offset=p['current']-segments[i]['initial'];targets[i]=p['target']-offset;bindings.append(dict(ink=p['ink'],index=i,offset=offset))
    return dict(axis=axis,ink=ink,segments=segments,targets=tuple(targets),bindings=bindings)

def positions(frame,g):
    out=[]
    for z in g['segments']:
        line=[frame[z['sample']][q]if g['axis']==1 else frame[q][z['sample']]for q in range(64)]
        vals=[q for q in range(z['bounds'][0],z['bounds'][1])if line[q]==g['ink']]
        out.append((min(vals)if z['side']=='min'else max(vals)+1)if vals else z['far'])
    return tuple(out)
