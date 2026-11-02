"""Infer editable rule schemas and solve bounded word equations from visible query pairs."""
from collections import defaultdict,deque
from panel_hypotheses_v2 import rectangles,digest
from panel_sequence_hypotheses import glyphs
from panel_control_learner import identity

def layouts(obs):
    rects=[dict(r,symbols=glyphs(r)) for r in rectangles(obs['frame']) if glyphs(r)]
    def separation(a,b):
        if a['background']==b['background']:return None
        y,x,Y,X=a['box'];r,c,R,C=b['box']
        if y+Y==r+R and Y-y==R-r and (X<c or C<x):return 'horizontal',max(c-X-1,x-C-1)
        if x+X==c+C and X-x==C-c and (Y<r or R<y):return 'vertical',max(r-Y-1,y-R-1)
        return None
    nearest={}
    for i,a in enumerate(rects):
        for axis in ('horizontal','vertical'):
            choices=[(q[1],j) for j,b in enumerate(rects) if j!=i and (q:=separation(a,b)) and q[0]==axis]
            if choices:
                best=min(d for d,j in choices);nearest[i,axis]={j for d,j in choices if d==best}
    groups=defaultdict(list)
    for (i,axis),indices in nearest.items():
        a=rects[i]
        for j in indices:
            if i not in nearest.get((j,axis),set()):continue
            b=rects[j]
            if any((q['box'][2]-q['box'][0]>q['box'][3]-q['box'][1])!=(axis=='vertical') for q in (a,b) if len(q['symbols'])>1):continue
            groups[a['background'],b['background'],axis].append((a,b))
    out=[]
    for (left,right,axis),pairs in sorted(groups.items()):
        if not 3<=len(pairs)<=6:continue
        pairs=sorted(pairs,key=lambda p:p[0]['box']);used={tuple(p['box']) for pair in pairs for p in pair}
        if len(used)!=2*len(pairs):continue
        panels=sorted([p for pair in pairs for p in pair],key=lambda p:p['box'])
        query=[]
        for a in rects:
            if a['box'] in used or a['background']!=left or len(a['symbols'])<2:continue
            for b in rects:
                if b['box'] in used or b['background']!=right or len(b['symbols'])<2:continue
                y,x,Y,X=a['box'];r,c,R,C=b['box'];h=Y-y+1;w=X-x+1;H=R-r+1;W=C-c+1
                aligned=(axis=='horizontal' and w>h and W>H and h==H and abs(x+X-c-C)<=1) or (axis=='vertical' and h>w and H>W and w==W and abs(y+Y-r-R)<=1)
                if aligned:query.append(dict(source_box=a['box'],target_box=b['box'],
                    source=tuple(identity(g['mask']) for g in a['symbols']),target=tuple(identity(g['mask']) for g in b['symbols']),
                    observation=digest(obs)))
        out.append(dict(source_background=left,target_background=right,axis=axis,pairs=pairs,panels=panels,queries=query,
            schema=tuple((len(a['symbols']),len(b['symbols'])) for a,b in pairs)))
    return out

def solutions(source,target,schema,cap=4096):
    """Assign every rule; enforce prefix-free inputs so the query has one parse."""
    queue=deque([(0,0,(None,)*len(schema),())]);seen=set();out={}
    while queue and len(seen)<cap:
        i,j,assigned,path=queue.popleft();key=(i,j,assigned)
        if key in seen:continue
        seen.add(key)
        if i==len(source) and j==len(target):
            if all(v is not None for v in assigned):out.setdefault(assigned,path)
            continue
        for k,(a,b) in enumerate(schema):
            if i+a>len(source) or j+b>len(target):continue
            rule=(source[i:i+a],target[j:j+b])
            if assigned[k] is not None and assigned[k]!=rule:continue
            if any(v is not None and m!=k and (rule[0][:len(v[0])]==v[0] or v[0][:len(rule[0])]==rule[0]) for m,v in enumerate(assigned)):continue
            child=list(assigned);child[k]=rule
            queue.append((i+a,j+b,tuple(child),path+((k,i,i+a,j,j+b),)))
    return dict(programs=sorted(out.items()),expanded=len(seen),overflow=bool(queue))

def signature(layout):
    return layout['source_background'],layout['target_background'],layout['axis'],layout['schema']

def proposals(layout,query):
    parsed=solutions(query['source'],query['target'],layout['schema'])
    if parsed['overflow']:return [],True
    result=[]
    for program,derivation in parsed['programs']:
        expected={}
        for (a,b),(left,right) in zip(layout['pairs'],program):
            expected[tuple(a['box'])]=left;expected[tuple(b['box'])]=right
        cells=[];classes=[];goal=[]
        for panel in layout['panels']:
            for i,g in enumerate(panel['symbols']):
                cells.append(dict(box=panel['box'],index=i,background=panel['background']))
                classes.append((panel['background'],identity(g['mask'])))
                goal.append((panel['background'],expected[tuple(panel['box'])][i]))
        box=(min(p['box'][0] for p in layout['panels']),min(p['box'][1] for p in layout['panels']),
             max(p['box'][2] for p in layout['panels']),max(p['box'][3] for p in layout['panels']))
        proof=dict(kind='editable_word_program',query=query,source_background=layout['source_background'],
            target_background=layout['target_background'],schema=layout['schema'],
            rule_boxes=[(a['box'],b['box']) for a,b in layout['pairs']],program=program,derivation=derivation,cells=cells,
            scope='Tentative prefix-free word transducer synthesized from a visible fixed input/output pair. Editing roles require actual action evidence; actual progress establishes sufficiency.')
        result.append(dict(box=box,source_box=query['source_box'],classes=tuple(classes),expected=tuple(goal),proposal=proof))
    return result,False
