"""Tentative aligned symbol centers from filled squares and simple hollow rings."""
from collections import defaultdict
import numpy as np
from scipy import ndimage
from indirect_word_geometry_v1 import frames,enclosed


def tokens(frame):
    a=np.asarray(frame);out={}
    for color in np.unique(a):
        lab,_=ndimage.label(a==color)
        for index,box in enumerate(ndimage.find_objects(lab),1):
            if box is None:continue
            y,x=box[0].start,box[1].start;h,w=box[0].stop-y,box[1].stop-x
            if h!=w or not 2<=h<=8:continue
            cut=a[box];solid=bool(np.all(cut==color))
            hollow=h>=4 and bool(np.all(cut[0]==color) and np.all(cut[-1]==color) and np.all(cut[:,0]==color) and np.all(cut[:,-1]==color))
            if hollow:
                inside=set(map(int,cut[1:-1,1:-1].ravel()));hollow=len(inside)==1 and int(color) not in inside
            if not solid and not hollow:continue
            size=2 if h%2==0 else 3;d=(h-size)//2;core=(y+d,x+d,size,size)
            value=int(a[y+d,x+d]);assert np.all(a[y+d:y+d+size,x+d:x+d+size]==value)
            token=dict(box=(y,x,h,w),core=core,color=int(color),value=value,hollow=bool(hollow))
            if core not in out or h>out[core]['box'][2]:out[core]=token
    return tuple(out[k] for k in sorted(out))


def layouts(frame):
    items=tokens(frame);groups=defaultdict(dict);out={}
    for token in items:
        y,x,h,w=token['core']
        for axis in (0,1):groups[axis,x if axis==0 else y,h,w][y if axis==0 else x]=token
    for (axis,fixed,h,w),by_pos in groups.items():
        positions=sorted(by_pos)
        for pitch in sorted({b-a for a in positions for b in positions if b-a>max(h,w)}):
            for start in positions:
                if start-pitch in by_pos:continue
                run=[];at=start
                while at in by_pos:run.append(by_pos[at]);at+=pitch
                if 3<=len(run)<=8:
                    row=tuple(t['core'] for t in run);out[row]=tuple(run)
    return {row:out[row] for row in sorted(out) if not any(set(row)<set(other) for other in out)}


def mixed_groups(frame):
    inventory=tokens(frame);result=[]
    for box,color in frames(frame):
        if box[0]==0 or box[1]==0:continue
        axis=1 if box[3]>box[2] else 0;groups=defaultdict(list)
        for t in inventory:
            c=t['core']
            if enclosed(t['box'],box):groups[c[1-axis],c[2],c[3]].append(t)
        options=[]
        for group in groups.values():
            group.sort(key=lambda t:t['core'][axis]);places=[t['core'][axis] for t in group]
            if 3<=len(group)<=8 and len(set(b-a for a,b in zip(places,places[1:])))==1:
                if len({t['box'][2] for t in group})>1:options.append(group)
        if len(options)==1:result.append(dict(box=box,color=color,axis=axis,tokens=tuple(options[0])))
    return tuple(result)
