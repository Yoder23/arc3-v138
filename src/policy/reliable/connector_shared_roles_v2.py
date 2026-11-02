"""Infer body/marker roles from repeated current-level visual evidence, not area alone."""
from collections import Counter
import numpy as np
from scipy import ndimage
from connector_assembly_geometry_v1 import initial
from connector_reveal_geometry_v4 import canonical
from connector_marker_parts_v1 import patches
from visual_transform_learner import digest

def objects(frame):
    f=np.asarray(frame);bg=Counter(f.ravel()).most_common(1)[0][0];labels,_=ndimage.label(f!=bg);out=[]
    for label,box in enumerate(ndimage.find_objects(labels),1):
        if box is None or box[0].start==0 or box[1].start==0 or box[0].stop==len(f) or box[1].stop==f.shape[1]:continue
        points=np.argwhere(labels[box]==label);counts=Counter(int(f[y+box[0].start,x+box[1].start]) for y,x in points)
        if len(counts)!=2 or len(points)>=f.size//4:continue
        body=min(counts,key=lambda c:(-counts[c],c));shape=tuple(sorted((int(y),int(x),int(f[y+box[0].start,x+box[1].start])) for y,x in points));out.append(dict(shape=shape,origin=(box[0].start,box[1].start),body=body))
    return sorted(out,key=lambda o:(o['origin'],o['shape']))

def interpret(obs,memory):
    scene=initial(obs['frame']);evidence={}
    for obj in list(memory.values())+[dict(o,memory_source=digest(obs),memory_template=o) for o in scene]:evidence[canonical(obj)]=obj
    counts=Counter(o['marker_color'] for o in evidence.values());top=counts.most_common()
    if not top or top[0][1]<2 or len(top)>1 and top[0][1]==top[1][1]:return scene
    marker=top[0][0];proofs=[dict(source=o['memory_source'],template=o['memory_template']) for o in evidence.values() if o['marker_color']==marker];out=[]
    for obj in objects(obs['frame']):
        colors={c for y,x,c in obj['shape']}
        if len(colors)!=2 or marker not in colors:continue
        body=next(c for c in colors if c!=marker);ps=patches(obj['shape'],marker)
        if not ps or len({len(p[2]) for p in ps})!=1 or min(len(p[2]) for p in ps)<4:continue
        piece=dict(shape=tuple((y,x,1 if c==body else 2) for y,x,c in obj['shape']),origin=obj['origin'],body_color=body,marker_color=marker)
        if body!=obj['body']:piece['role_hypothesis']=dict(kind='shared_marker_color',color=marker,support=proofs)
        out.append(piece)
    return out if out else scene
