"""Jointly assign revealed and concealed pieces instead of committing to a local fragment match."""
from connector_reveal_geometry_v4 import initial,solve,valid,absolute,complete,canonical,colored_locate,locate as prior_locate
from composite_connector_learner_v5 import rotate
from collections import Counter
import numpy as np
from scipy.signal import correlate2d

def locate(frame,templates):
    old=prior_locate(frame,templates);inks={o['body_color'] for o in templates if o.get('hidden')}
    if len(inks)!=1:return old
    ink=next(iter(inks));f=np.asarray(frame);universe={tuple(map(int,q)) for q in np.argwhere(f==ink) if 7<=q[0]<62}
    if all(old) and valid(old) and universe<={q for o in old for q in absolute(o)}:return old
    colored=colored_locate(frame,templates);ports={q for o in colored if o for q,v in absolute(o).items() if v==2};bodymask=(f==ink).astype(np.int32);portmask=bodymask.copy()
    for y,x in ports:portmask[y,x]=1
    choices={}
    for i,template in enumerate(templates):
        candidates={}
        def add(obj):
            obj=dict(obj)
            if obj['body_color']==ink:obj['hidden']=True
            for k in ('memory_source','memory_template','role_hypothesis'):
                if k in template:obj[k]=template[k]
            candidates[(obj['shape'],obj['origin'],obj['body_color'])]=obj
        if colored[i]:add(colored[i])
        if old[i]:add(old[i])
        for turn in range(4):
            shape=rotate(template['shape'],turn);h=1+max(y for y,x,c in shape);w=1+max(x for y,x,c in shape);b=np.zeros((h,w),dtype=np.int32);m=b.copy()
            for y,x,c in shape:(b if c==1 else m)[y,x]=1
            possible=(correlate2d(bodymask,b,mode='valid')==int(b.sum()))&(correlate2d(portmask,m,mode='valid')==int(m.sum()))
            for y,x in np.argwhere(possible):
                obj=dict(shape=shape,origin=(int(y),int(x)),body_color=ink,marker_color=template['marker_color'],hidden=True,joint_silhouette_recall=True)
                if valid([obj]):add(obj)
        choices[i]=list(candidates.values())
        if len(choices[i])>2048:return old if not all(old) else [None]*len(old)
    # Constraint propagation removes fragment matches inside other uniquely located pieces.
    changed=True
    while changed:
        changed=False
        for i in choices:
            supported=[obj for obj in choices[i] if all(any(valid([obj,other]) for other in choices[j]) for j in choices if j!=i)]
            if len(supported)!=len(choices[i]):choices[i]=supported;changed=True
        if any(not v for v in choices.values()):return old if not all(old) else [None]*len(old)
    if any(len(v)>128 for v in choices.values()):return old if not all(old) else [None]*len(old)
    solutions=[];nodes=0
    def search(assigned,pending):
        nonlocal nodes
        nodes+=1
        if nodes>4096 or len(solutions)>1:return
        if not pending:
            if universe<={q for o in assigned.values() for q in absolute(o)}:solutions.append(dict(assigned))
            return
        i=min(pending,key=lambda j:len(choices[j]))
        for obj in choices[i]:
            if valid(list(assigned.values())+[obj]):assigned[i]=obj;search(assigned,[j for j in pending if j!=i]);del assigned[i]
    search({},list(range(len(templates))))
    if len(solutions)==1 and nodes<=4096:return [solutions[0][i] for i in range(len(templates))]
    return old if not all(old) else [None]*len(old)
