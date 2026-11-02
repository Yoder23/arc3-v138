"""Extend an observed regular lattice to partially populated miniature neighborhoods."""
from collections import Counter, defaultdict
import numpy as np
from nested_pattern_perception import representations

def expanded(frame, memory):
    a=np.asarray(frame);background=Counter(v for row in frame for v in row).most_common(1)[0][0]
    output=[]
    for anchor in representations(frame):
        size=anchor['size'];sy,sx=anchor['pitch']
        if size%3:continue
        oy,ox=anchor['cells'][0][0]%sy,anchor['cells'][0][1]%sx
        uniform={};patterns={};n=size//3
        for y in range(oy,len(a)-size+1,sy):
            for x in range(ox,a.shape[1]-size+1,sx):
                patch=a[y:y+size,x:x+size]
                if np.all(patch==patch[0,0]):
                    if int(patch[0,0])!=background:uniform[y,x]=int(patch[0,0])
                    continue
                blocks=[[patch[i*n:(i+1)*n,j*n:(j+1)*n] for j in range(3)] for i in range(3)]
                if all(np.all(q==q[0,0]) for row in blocks for q in row):
                    patterns[y,x]=tuple(tuple(int(q[0,0]) for q in row) for row in blocks)
        for m in memory:
            ink,flip,turn=m['rule']
            inks={v for ex in m['examples'] for i,row in enumerate(ex['pattern']) for j,v in enumerate(row) if (i,j)!=(1,1)}
            if len(inks)!=2 or ink not in inks:continue
            con=defaultdict(lambda:dict(equal=set(),unequal=set()));markers=[]
            for (y,x),pattern in sorted(patterns.items()):
                if pattern[1][1] in inks or pattern[1][1] not in set(uniform.values()):continue
                if sum(pattern[i][j] in inks for i in range(3) for j in range(3) if (i,j)!=(1,1))<2:continue
                markers.append(dict(box=(y,x,size,size),pattern=pattern))
                p=np.asarray(pattern);p=np.rot90(np.fliplr(p) if flip else p,turn)
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        if not(dy or dx):continue
                        pos=y+dy*sy,x+dx*sx;v=int(p[dy+1,dx+1])
                        if pos in uniform and v in inks:
                            con[pos]['equal' if v==ink else 'unequal'].add(int(p[1,1]))
            if len(markers)<=len(anchor['markers']) or len(con)<=len(anchor['cells']):continue
            if any(len(v['equal'])>1 or v['equal']&v['unequal'] for v in con.values()):continue
            output.append(dict(anchor=anchor,size=size,pitch=(sy,sx),background=background,inks=sorted(inks),
                markers=markers,cells=[(y,x,uniform[y,x]) for y,x in sorted(con)],
                constraints=[dict(y=y,x=x,equal=sorted(v['equal']),unequal=sorted(v['unequal'])) for (y,x),v in sorted(con.items())],memory=m))
    return sorted(output,key=lambda p:(-len(p['cells']),-len(p['markers']),tuple(p['memory']['rule'])))
