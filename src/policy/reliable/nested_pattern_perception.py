"""Detect uniform cell lattices surrounding observed miniature3x3 patterns."""
from collections import Counter,defaultdict
import numpy as np
from scipy import ndimage

def marker_pattern(patch):
    h,w=patch.shape
    if h!=w or h%3:return None
    n=h//3;pattern=[]
    for y in range(3):
        row=[]
        for x in range(3):
            q=patch[y*n:(y+1)*n,x*n:(x+1)*n]
            if not np.all(q==q[0,0]):return None
            row.append(int(q[0,0]))
        pattern.append(row)
    outside={pattern[y][x] for y in range(3) for x in range(3) if (y,x)!=(1,1)}
    if len(outside)!=2 or pattern[1][1] in outside:return None
    return tuple(map(tuple,pattern))

def representations(frame):
    a=np.asarray(frame);groups=defaultdict(dict)
    for color in np.unique(a):
        labels,_=ndimage.label(a==color)
        for i,s in enumerate(ndimage.find_objects(labels),1):
            if s is None:continue
            h=s[0].stop-s[0].start;w=s[1].stop-s[1].start
            if 3<=h==w<=12 and np.all(labels[s]==i):
                groups[h][(s[0].start,s[1].start)]=int(color)
    results=[]
    for size,lookup in groups.items():
        if len(lookup)<8:continue
        dx=Counter();dy=Counter()
        for y in {p[0] for p in lookup}:
            xs=sorted(x for yy,x in lookup if yy==y)
            dx.update(b-a for a,b in zip(xs,xs[1:]) if size<b-a<=size*3)
        for x in {p[1] for p in lookup}:
            ys=sorted(y for y,xx in lookup if xx==x)
            dy.update(b-a for a,b in zip(ys,ys[1:]) if size<b-a<=size*3)
        for sy,_ in dy.most_common(3):
            for sx,_ in dx.most_common(3):
                possible={(y+dy*sy,x+dx*sx) for y,x in lookup for dy in (-1,0,1) for dx in (-1,0,1)}
                markers=[]
                for y,x in sorted(possible):
                    if not(0<=y<=len(a)-size and 0<=x<=a.shape[1]-size) or marker_pattern(a[y:y+size,x:x+size]) is None:continue
                    neighbors=tuple((y+dy*sy,x+dx*sx) for dy in (-1,0,1) for dx in (-1,0,1) if dy or dx)
                    if all(p in lookup for p in neighbors):
                        markers.append(dict(box=(y,x,size,size),pattern=marker_pattern(a[y:y+size,x:x+size]),neighbors=neighbors,
                                            colors=tuple(lookup[p] for p in neighbors)))
                if not markers:continue
                cells=sorted({p for m in markers for p in m['neighbors']})
                results.append(dict(size=size,pitch=(sy,sx),markers=markers,
                                    cells=tuple((y,x,lookup[y,x]) for y,x in cells)))
    return sorted(results,key=lambda r:(-len(r['markers']),-len(r['cells']),r['size'],r['pitch']))
