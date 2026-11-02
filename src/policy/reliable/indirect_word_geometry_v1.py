"""Tentative ordered leaf expansion from visible framed groups and connected handles."""
from collections import Counter,defaultdict,deque
from functools import lru_cache
import numpy as np
from scipy import ndimage

def border(box):
    y,x,h,w=box
    return {(y,u) for u in range(x,x+w)}|{(y+h-1,u) for u in range(x,x+w)}|{(v,x) for v in range(y,y+h)}|{(v,x+w-1) for v in range(y,y+h)}

def enclosed(inner,outer):
    y,x,h,w=inner;a,b,c,d=outer
    return a<y and b<x and y+h<a+c and x+w<b+d

def maximal_rectangles(rectangles, height, width):
    # For each ink, prefix over outer top/left and suffix over outer bottom.
    # The stored maximum outer right answers all four strict inequalities.
    groups=defaultdict(list)
    for box,color in rectangles:groups[color].append(box)
    kept=[]
    for color,boxes in groups.items():
        index=np.full((height,width,height+1),-1,dtype=np.int32)
        for y,x,h,w in boxes:index[y,x,y+h]=max(index[y,x,y+h],x+w)
        np.maximum.accumulate(index,axis=0,out=index)
        np.maximum.accumulate(index,axis=1,out=index)
        reverse=index[:,:,::-1]
        np.maximum.accumulate(reverse,axis=2,out=reverse)
        for box in boxes:
            y,x,h,w=box;bottom=y+h;right=x+w
            enclosed=bool(y and x and bottom<height and index[y-1,x-1,bottom+1]>right)
            if not enclosed:kept.append((box,color))
    return tuple(sorted(kept))


def horizontal_frames(f):
    H,W=len(f),len(f[0]);bg=Counter(v for r in f for v in r).most_common(1)[0][0];out=set()
    # Crossing connectors may occlude a border. Three sides must
    # remain complete and the fourth retain at least three quarters of its ink.
    for y,row in enumerate(f):
        x=0
        while x<W:
            z=x+1
            while z<W and row[z]==row[x]:z+=1
            color=row[x];w=z-x
            if color!=bg and w>=5:
                for other in range(H):
                    h=abs(other-y)+1
                    if h<5 or max(h,w)<8 or max(h,w)<1.5*min(h,w):continue
                    top=min(y,other)
                    if not all(f[v][x]==f[v][z-1]==color for v in range(top,top+h)):continue
                    missing=[u for u in range(x,z) if f[other][u]!=color]
                    if len(missing)>w//4:continue
                    out.add(((top,x,h,w),color))
            x=z
    # Avoid cropped rectangles accidentally constructed from another full row.
    return maximal_rectangles(out,H,W)

def frames(f):
    out=set(horizontal_frames(f))
    transposed=tuple(zip(*f))
    for (y,x,h,w),color in horizontal_frames(transposed):out.add(((x,y,w,h),color))
    return tuple(sorted(out))

def components(f):
    a=np.asarray(f);small=[];labels={}
    for color in np.unique(a):
        lab,_=ndimage.label(a==color);labels[int(color)]=lab
        for k,s in enumerate(ndimage.find_objects(lab),1):
            if s is None:continue
            h,w=s[0].stop-s[0].start,s[1].stop-s[1].start
            if 2<=min(h,w) and max(h,w)<=12 and int(np.count_nonzero(lab[s]==k))==h*w:
                small.append((s[0].start,s[1].start,h,w))
    return sorted(small),labels

@lru_cache(maxsize=64)
def _parse(f):
    rectangles=frames(f);small,labels=components(f);groups={}
    background=Counter(v for row in f for v in row).most_common(1)[0][0]
    def empty(box):
        y,x,h,w=box
        return 2*sum(f[v][u]==background for v in range(y+1,y+h-1) for u in range(x+1,x+w-1)) >= (h-2)*(w-2)

    for box,color in rectangles:
        axis=1 if box[3]>box[2] else 0;bins=defaultdict(list)
        for cell in small:
            if enclosed(cell,box):bins[(cell[1-axis],cell[2],cell[3])].append(cell)
        candidates=[]
        for cells in bins.values():
            cells=sorted(cells,key=lambda b:b[axis]);places=[b[axis] for b in cells]
            if 2<=len(cells)<=8 and len(set(b-a for a,b in zip(places,places[1:])))==1:
                candidates.append(tuple(cells))
        if len(candidates)==1:groups[box]=dict(box=box,color=color,axis=axis,cells=candidates[0])
    edges={};ambiguous=set()
    for box,g in groups.items():
        for i,cell in enumerate(g['cells']):
            y,x,h,w=cell;ring=(y-1,x-1,h+2,w+2)
            if min(y,x)<1 or y+h>=len(f) or x+w>=len(f[0]):continue
            pixels=border(ring);colors={f[v][u] for v,u in pixels}
            if len(colors)!=1:continue
            color=next(iter(colors));lab=labels[color];component=int(lab[y-1,x-1]);matches=[]
            for child,c in groups.items():
                if child==box or c['color']!=color:continue
                # The complete child's border is connected to the handle.
                child_pixels=[(v,u) for v,u in border(child) if f[v][u]==color]
                if child_pixels and all(int(lab[v,u])==component for v,u in child_pixels):matches.append(child)
            mode='connected'
            if not matches and empty(box):
                matches=[child for child,c in groups.items() if child!=box and c['color']==color
                         and empty(child) and all(tuple(t[2:])==(h,w) for t in c['cells'])]
                mode='unique_ink_reference'
            if len(matches)==1:edges[box,i]=dict(child=matches[0],ring=ring,color=color,mode=mode)
            elif len(matches)>1:ambiguous.add(box)
    result=[]
    for root in groups:
        if not any(b==root for b,i in edges):continue
        nodes=[];links=[];visited=set()
        def expand(box):
            if box in visited or box in ambiguous:raise ValueError('Cycle,shared child or ambiguous link')
            visited.add(box);g=groups[box];nodes.append(g);leaves=[]
            for i,cell in enumerate(g['cells']):
                edge=edges.get((box,i))
                if edge:
                    links.append(dict(parent=box,slot=i,**edge));leaves.extend(expand(edge['child']))
                else:leaves.append(cell)
            return leaves
        try:leaves=expand(root)
        except ValueError:continue
        if 3<=len(leaves)<=8 and len(set(leaves))==len(leaves):
            result.append(dict(root=root,nodes=nodes,links=links,leaves=tuple(leaves),
                hypothesis='A connected handle or a unique same-ink separated frame with matching slot shape and background interior may substitute ordered child slots. Reference roles and the resulting word are tentative hypotheses, not supplied goals.'))
    return tuple(result)

def parse(frame):return _parse(tuple(map(tuple,frame)))
