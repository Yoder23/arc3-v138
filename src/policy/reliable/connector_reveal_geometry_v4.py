"""Retrieve observed marker layouts through matching concealed silhouettes."""
from collections import Counter
import numpy as np
from scipy import ndimage
from scipy.signal import correlate2d
from connector_assembly_geometry_v1 import initial,solve,valid,absolute,complete,locate as connected_body_locate
from composite_connector_learner_v5 import rotate

def colored_locate(frame,templates):
    """Match a remembered body even when a central marker separates its lobes."""
    found=connected_body_locate(frame,templates);f=np.asarray(frame);bg=Counter(f.ravel()).most_common(1)[0][0]
    for i,template in enumerate(templates):
        if found[i] is not None:continue
        matches={}
        for turn in range(4):
            shape=rotate(template['shape'],turn);h=1+max(y for y,x,c in shape);w=1+max(x for y,x,c in shape);body=np.zeros((h,w),dtype=np.int32);marker=body.copy()
            for y,x,c in shape:(body if c==1 else marker)[y,x]=1
            if ndimage.label(body)[1]<2:continue
            for color in sorted(set(f.ravel())-{bg}):
                labs,_=ndimage.label(f==color);sizes=np.bincount(labs.ravel());body_matches=correlate2d((f==color).astype(np.int32),body,mode='valid')==int(body.sum());port_matches=correlate2d(((f!=color)&(f!=bg)).astype(np.int32),marker,mode='valid')==int(marker.sum())
                for y,x in np.argwhere(body_matches&port_matches):
                    origin=(int(y),int(x));points=[(int(y)+a,int(x)+b) for a,b,c in shape if c==1];labels=Counter(int(labs[a,b]) for a,b in points)
                    if 0 in labels or any(sizes[k]!=n for k,n in labels.items()):continue
                    if any(not(0<a+origin[0]<63 and 0<b+origin[1]<63) for a,b,c in shape):continue
                    matches[(shape,origin)]=dict(shape=shape,origin=origin,body_color=int(color),marker_color=template['marker_color'],disconnected_body_recall=True)
        if len(matches)==1:found[i]=next(iter(matches.values()))
    return found

def canonical(obj):return min(rotate(obj['shape'],t) for t in range(4))
def locate(frame,templates):
    known=colored_locate(frame,templates);f=np.asarray(frame);bg=Counter(f.ravel()).most_common(1)[0][0];components=[]
    for color in sorted(set(f.ravel())-{bg}):
        labs,_=ndimage.label(f==color)
        for i,box in enumerate(ndimage.find_objects(labs)):
            if box is None or box[0].start==0 or box[1].start==0 or box[0].stop==64 or box[1].stop==64:continue
            cells=set(map(tuple,np.argwhere(labs[box]==i+1).tolist()));components.append((int(color),(box[0].start,box[1].start),cells))
    out=[]
    for i,template in enumerate(templates):
        obj=known[i]
        if obj is None:
            matches={}
            for t in range(4):
                shape=rotate(template['shape'],t);mask={(y,x) for y,x,c in shape}
                for color,origin,cells in components:
                    if cells==mask:matches[(shape,origin)]=dict(shape=shape,origin=origin,body_color=color,marker_color=template['marker_color'],hidden=True)
            obj=next(iter(matches.values())) if len(matches)==1 else None
        if obj:
            for key in ('memory_source','memory_template','role_hypothesis'):
                if key in template:obj[key]=template[key]
        out.append(obj)
    missing=[i for i,obj in enumerate(out) if obj is None]
    inks={obj['body_color'] for obj in templates if obj.get('hidden')}
    if missing and len(inks)==1:
        ink=next(iter(inks));universe={(int(y),int(x)) for y,x in np.argwhere(f==ink) if 7<=y<62};known=[obj for obj in out if obj];visible_markers={q for obj in known if not obj.get('hidden') for q,c in absolute(obj).items() if c==2};bodymask=(f==ink).astype(np.int32);portmask=bodymask.copy()
        for y,x in visible_markers:portmask[y,x]=1
        choices={};overflow=False
        for i in missing:
            candidates={};template=templates[i]
            for turn in range(4):
                shape=rotate(template['shape'],turn);h=1+max(y for y,x,c in shape);w=1+max(x for y,x,c in shape);b=np.zeros((h,w),dtype=np.int32);m=b.copy()
                for y,x,c in shape:(b if c==1 else m)[y,x]=1
                matches=(correlate2d(bodymask,b,mode='valid')==int(b.sum()))&(correlate2d(portmask,m,mode='valid')==int(m.sum()))
                for y,x in np.argwhere(matches):
                    obj=dict(shape=shape,origin=(int(y),int(x)),body_color=ink,marker_color=template['marker_color'],hidden=True,joint_silhouette_recall=True)
                    if not valid(known+[obj]):continue
                    for key in ('memory_source','memory_template','role_hypothesis'):
                        if key in template:obj[key]=template[key]
                    candidates[(shape,obj['origin'])]=obj
            choices[i]=list(candidates.values())
            if len(choices[i])>64:overflow=True
        solutions=[];nodes=0
        def search(assigned,pending):
            nonlocal nodes
            nodes+=1
            if nodes>4096 or len(solutions)>1:return
            if not pending:
                occupied={q for obj in assigned.values() for q in absolute(obj) if f[q]==ink}
                if universe<=occupied:solutions.append(dict(assigned))
                return
            i=min(pending,key=lambda j:len(choices[j]))
            for obj in choices[i]:
                if valid(list(assigned.values())+[obj]):assigned[i]=obj;search(assigned,[j for j in pending if j!=i]);del assigned[i]
        if not overflow:search({i:obj for i,obj in enumerate(out) if obj},missing)
        if len(solutions)==1 and nodes<=4096:out=[solutions[0].get(i) for i in range(len(templates))]
    return out
