"""Hypothesize majority-valued cells while preserving every visible decoration."""
from collections import Counter
import numpy as np
from scipy import ndimage
from decorated_nested_perception_v2 import expanded
def project(frame):
    a=np.asarray(frame);proxy=a.copy();bg=Counter(a.ravel().tolist()).most_common(1)[0][0]
    labels,_=ndimage.label(a!=bg);decorations=[]
    for i,box in enumerate(ndimage.find_objects(labels),1):
        if box is None:continue
        y,x=box[0].start,box[1].start;s=box[0].stop-y
        if not(3<=s<=12 and s%3==0 and box[1].stop-x==s and np.all(labels[box]==i)):continue
        patch=a[box];n=s//3;blocks=[[patch[j*n:(j+1)*n,k*n:(k+1)*n] for k in range(3)] for j in range(3)]
        if not all(np.all(q==q[0,0]) for row in blocks for q in row):continue
        pattern=[[int(q[0,0]) for q in row] for row in blocks];value=pattern[1][1];counts=Counter(v for row in pattern for v in row)
        if len(counts)!=2 or counts[value] not in (7,8):continue
        decorations.append(dict(box=[y,x,s,s],pattern=pattern,value=value,majority_blocks=counts[value]))
        proxy[box]=value
    return proxy.tolist(),decorations
def layout(frame,memory):
    proxy,decorations=project(frame)
    if len(decorations)<8:return None
    scenes=expanded(proxy,memory)
    if not scenes:return None
    p=scenes[0];size=p['size'];sy,sx=p['pitch'];oy,ox=p['cells'][0][0]%sy,p['cells'][0][1]%sx
    palette=sorted({v for y,x,v in p['cells']}|{m['pattern'][1][1] for m in p['markers']});a=np.asarray(frame);q=np.asarray(proxy)
    variables=[]
    for y in range(oy,len(a)-size+1,sy):
        for x in range(ox,a.shape[1]-size+1,sx):
            patch=a[y:y+size,x:x+size];v=int(patch[size//2,size//2])
            if v not in palette or not np.all(q[y:y+size,x:x+size]==v):continue
            mask=patch==v
            variables.append(dict(y=y,x=x,value=v,mask=mask.tolist(),fixed=np.where(mask,-1,patch).tolist(),structured=not bool(np.all(mask))))
    from collections import defaultdict
    con=defaultdict(lambda:dict(equal=set(),unequal=set()));positions={(v['y'],v['x']) for v in variables};ink,flip,turn=p['memory']['rule']
    for m in p['markers']:
        y,x,_,_=m['box'];q=np.asarray(m['pattern']);q=np.rot90(np.fliplr(q) if flip else q,turn)
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if not(dy or dx):continue
                pos=y+dy*sy,x+dx*sx;v=int(q[dy+1,dx+1])
                if pos in positions and v in p['inks']:con[pos]['equal' if v==ink else 'unequal'].add(int(q[1,1]))
    if any(len(c['equal'])>1 or c['equal']&c['unequal'] for c in con.values()):return None
    return dict(size=size,pitch=(sy,sx),palette=palette,variables=variables,
        constraints=[dict(y=y,x=x,equal=sorted(c['equal']),unequal=sorted(c['unequal'])) for (y,x),c in sorted(con.items())],
        source=p['memory']['source'],examples=p['memory']['examples'],rule=p['memory']['rule'],anchor=p['anchor'],markers=p['markers'],
        inks=p['inks'],background=p['background'],decorations=decorations,
        projection_scope='Tentative majority-valued cells with observed fixed decoration; no effect asserted until actual clicks. Original frames remain unchanged.')
