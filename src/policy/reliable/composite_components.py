"""Connected two-color appearance hypotheses; no privileged background color."""
from collections import defaultdict,deque

def palette(label):
    if type(label) is not int:raise ValueError('Appearance identifier must be integer')
    if 0<=label<16:return {label}
    mask=label-16
    if not 0<mask<65536 or mask.bit_count()!=2:raise ValueError('Invalid palette appearance identifier')
    return {v for v in range(16) if mask&(1<<v)}

def append_composites(frame,primitives):
    height,width=len(frame),len(frame[0]);owner={}
    for i,c in enumerate(primitives):
        for p in c['cells_rc']:owner[tuple(p)]=i
    links=defaultdict(set);pairs=set();by_color=defaultdict(set)
    for i,c in enumerate(primitives):by_color[c['label']].add(i)
    for (y,x),i in owner.items():
        for q in ((y+1,x),(y,x+1)):
            j=owner.get(q)
            if j is not None and i!=j:
                links[i].add(j);links[j].add(i)
                pairs.add(tuple(sorted((primitives[i]['label'],primitives[j]['label']))))
    out=list(primitives)
    for colors in sorted(pairs):
        unseen=set().union(*(by_color[c] for c in colors))
        while unseen:
            start=min(unseen);unseen.remove(start);queue=deque([start]);group=[]
            while queue:
                i=queue.popleft();group.append(i)
                for j in sorted(links[i]&unseen):unseen.remove(j);queue.append(j)
            if {primitives[i]['label'] for i in group}!=set(colors):continue
            cells=sorted(tuple(p) for i in group for p in primitives[i]['cells_rc'])
            # A broad authored object-size prior, not a game/color whitelist.
            if len(cells)>=height*width/4:continue
            top,left=min(y for y,x in cells),min(x for y,x in cells)
            out.append(dict(label=16+sum(1<<c for c in colors),palette=list(colors),
                origin_rc=[top,left],shape_rc=[[y-top,x-left] for y,x in cells],
                cells_rc=[list(p) for p in cells],size=len(cells),
                interpretation='connected_palette_appearance_not_identity_proof'))
    return out

def subsume_parts(candidates,frame,components):
    """Prefer a supported connected whole over its co-moving proper parts.

    Disconnected synchronized objects never qualify here. This is an appearance
    model-selection prior, not evidence of physical attachment or agency.
    """
    located=[]
    for candidate in candidates:
        actor=candidate['actor']
        matches=[c for c in components if c['label']==actor['label'] and c['shape_rc']==actor['shape_rc']]
        located.append({tuple(p) for p in matches[0]['cells_rc']} if len(matches)==1 else None)
    remove=set()
    for i,a in enumerate(candidates):
        if located[i] is None:continue
        ae={r['evidence_hash']:r for r in a['support']}
        for j,b in enumerate(candidates):
            if i==j or located[j] is None or not located[i]<located[j] or b['actor']['label']<16:continue
            be={r['evidence_hash']:r for r in b['support']};common=set(ae)&set(be)
            if len(common)<4 or len({ae[k]['action'] for k in common})<2:continue
            def contained(k):
                left,right=ae[k],be[k]
                if left['delta']!=right['delta']:return False
                for key in ('before_rc','after_rc'):
                    if key not in left or key not in right:return False
                    ly,lx=left[key];ry,rx=right[key]
                    lc={(ly+y,lx+x) for y,x in a['actor']['shape_rc']}
                    rc={(ry+y,rx+x) for y,x in b['actor']['shape_rc']}
                    if not lc<rc:return False
                return True
            action_a={r['action']:r['delta'] for r in a['support']}
            action_b={r['action']:r['delta'] for r in b['support']}
            if all(action_a[k]==action_b[k] for k in set(action_a)&set(action_b)) and all(contained(k) for k in common):remove.add(i)
    return [c for i,c in enumerate(candidates) if i not in remove]
