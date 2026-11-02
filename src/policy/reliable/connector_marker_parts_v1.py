"""Literal marker-patch geometry for reusable assembly hypotheses."""
from collections import Counter
from composite_connector_learner_v5 import identity,rotate

def patches(shape,color):
    remaining={(y,x) for y,x,c in shape if c==color};out=[]
    while remaining:
        start=min(remaining);remaining.remove(start);todo=[start];cells=set()
        while todo:
            y,x=todo.pop();cells.add((y,x))
            for p in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                if p in remaining:remaining.remove(p);todo.append(p)
        y=min(a for a,b in cells);x=min(b for a,b in cells);norm=tuple(sorted((a-y,b-x) for a,b in cells));out.append((norm,(y,x),cells))
    return out

def marker_types(actor):
    result=set()
    for turn in range(4):
        shape=rotate(actor['shape'],turn);body=actor.get('body',Counter(c for y,x,c in shape).most_common(1)[0][0])
        for color in {c for y,x,c in shape}-{body}:
            ps=patches(shape,color)
            if 1<=len(ps)<=12 and len({len(p[2]) for p in ps})==1:
                result.update(p[0] for p in ps if 4<=len(p[2])<=36)
    return result

def hypotheses(actor,others):
    out=[];seen=set()
    for target in others:
        if identity(target)==identity(actor):continue
        for turn in range(4):
            shape=rotate(actor['shape'],turn)
            for color in ({c for y,x,c in shape}-{actor['body']})&({c for y,x,c in target['shape']}-{target['body']}):
                aa=patches(shape,color);tt=patches(target['shape'],color)
                for sig,ao,acells in aa:
                    if not 4<=len(sig)<=36:continue
                    for other,to,tcells in tt:
                        if other!=sig:continue
                        origin=(target['origin'][0]+to[0]-ao[0],target['origin'][1]+to[1]-ao[1]);key=(shape,origin,target['origin'])
                        if key in seen:continue
                        seen.add(key);ac={(y+origin[0],x+origin[1]):c for y,x,c in shape};tc={(y+target['origin'][0],x+target['origin'][1]):c for y,x,c in target['shape']};shared=ac.keys()&tc.keys()
                        if not shared or any(ac[q]!=color or tc[q]!=color for q in shared):continue
                        aset=[{(y+origin[0],x+origin[1]) for y,x in p[2]} for p in aa];tset=[{(y+target['origin'][0],x+target['origin'][1]) for y,x in p[2]} for p in tt]
                        if any(p&shared and not p<=shared for p in aset+tset):continue
                        full=shared=={q for q,v in ac.items() if v==color}=={q for q,v in tc.items() if v==color}
                        out.append(dict(shape=shape,origin=origin,connector_color=color,target=target,interpretation='coincidence' if full else 'marker_subset',marker_shape=sig,scope='Whole literal marker patches overlap; partial assembly is an unconfirmed intermediate-goal hypothesis.'))
    return sorted(out,key=lambda g:(g['interpretation']!='coincidence',g['origin']))
