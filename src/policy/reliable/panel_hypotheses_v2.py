"""Observable multicolor panels and tentative example-to-sequence correspondences.

No colors, coordinates, game IDs or glyphs are assigned fixed semantic roles.
The resulting mappings are interpretation hypotheses, not known puzzle goals.
"""
import hashlib,json
from collections import defaultdict

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rectangles(frame):
    h=len(frame);w=len(frame[0]);seen=set();out=[]
    for y in range(h):
        for x in range(w):
            if (y,x) in seen:continue
            color=frame[y][x];todo=[(y,x)];seen.add((y,x));cells=[]
            while todo:
                yy,xx=todo.pop();cells.append((yy,xx))
                for a,b in ((yy-1,xx),(yy+1,xx),(yy,xx-1),(yy,xx+1)):
                    if 0<=a<h and 0<=b<w and (a,b) not in seen and frame[a][b]==color:seen.add((a,b));todo.append((a,b))
            a=min(q[0] for q in cells);b=min(q[1] for q in cells);c=max(q[0] for q in cells);d=max(q[1] for q in cells)
            if min(c-a+1,d-b+1)<5 or (c-a+1)*(d-b+1)>h*w//2:continue
            border={(r,k) for r in range(a,c+1) for k in range(b,d+1) if r in (a,c) or k in (b,d)}
            if not all(frame[r][k]==color for r,k in border):continue
            ink=tuple((r,k) for r in range(a+1,c) for k in range(b+1,d) if frame[r][k]!=color)
            if ink:out.append(dict(box=(a,b,c,d),background=color,ink=ink))
    return sorted(out,key=lambda r:(r['box'],r['background']))
def normalized(cells):
    if not cells:return ()
    y=min(p[0] for p in cells);x=min(p[1] for p in cells)
    return tuple(sorted((r-y,c-x) for r,c in cells))
def glyphs(rect):
    a,b,c,d=rect['box'];h=c-a+1;w=d-b+1
    if max(h,w)<2*min(h,w):return [dict(mask=normalized(rect['ink']),point=((b+d)//2,(a+c)//2))]
    axis=1 if w>h else 0;used=sorted({p[axis] for p in rect['ink']});groups=[]
    for v in used:
        if not groups or v>groups[-1][-1]+1:groups.append([v])
        else:groups[-1].append(v)
    out=[]
    for group in groups:
        ink=[p for p in rect['ink'] if group[0]<=p[axis]<=group[-1]]
        out.append(dict(mask=normalized(ink),point=((min(p[1] for p in ink)+max(p[1] for p in ink))//2,(min(p[0] for p in ink)+max(p[0] for p in ink))//2)))
    return out

def transformed(mask,turn,flip):
    cells=[(y,-x if flip else x) for y,x in mask]
    for _ in range(turn):cells=[(-x,y) for y,x in cells]
    return normalized(cells)
def recognize(mask,mapping):
    matches=[dict(example=source,turn=k,reflection=f,target=target) for source,target in mapping.items() for k in range(4) for f in (False,True) if transformed(source,k,f)==mask]
    targets={m['target'] for m in matches}
    if len(targets)!=1:return None
    return dict(expected=next(iter(targets)),matches=matches,transport_alternatives=sorted({transformed(m['target'],m['turn'],m['reflection']) for m in matches}))

def candidates(obs):
    frame=obs['frame'];proof=digest(obs);rects=rectangles(frame);singles=[];bars=[]
    for r in rects:
        a,b,c,d=r['box'];h=c-a+1;w=d-b+1
        (singles if max(h,w)<2*min(h,w) else bars).append(r)
    def distance(a,b):
        y,x,Y,X=a['box'];r,c,R,C=b['box']
        if (Y-y,X-x)!=(R-r,C-c) or a['background']==b['background']:return None
        if y+Y==r+R:return abs(x+X-c-C)
        if x+X==c+C:return abs(y+Y-r-R)
        return None
    nearest={}
    for i,r in enumerate(singles):
        choices=[(distance(r,q),j) for j,q in enumerate(singles) if j!=i and distance(r,q) is not None]
        if choices:
            best=min(d for d,j in choices);nearest[i]={j for d,j in choices if d==best}
    grouped=defaultdict(list)
    for i,targets in nearest.items():
        for j in targets:
            if i not in nearest.get(j,set()):continue
            r,q=singles[i],singles[j];a,b=normalized(r['ink']),normalized(q['ink'])
            grouped[(r['background'],q['background'])].append(dict(source_mask=a,target_mask=b,source_box=r['box'],target_box=q['box'],observation=proof))
    maps=[]
    for (left,right),examples in sorted(grouped.items()):
        mapping=defaultdict(set)
        for e in examples:mapping[e['source_mask']].add(e['target_mask'])
        if len(mapping)<3 or any(len(v)!=1 for v in mapping.values()):continue
        maps.append(dict(source_background=left,target_background=right,mapping={k:next(iter(v)) for k,v in mapping.items()},examples=examples))
    proposals=[]
    for m in maps:
        for left in bars:
            if left['background']!=m['source_background']:continue
            source=glyphs(left)
            recognition=[recognize(g['mask'],m['mapping']) for g in source]
            if len(source)<2 or any(v is None for v in recognition):continue
            expected=tuple(v['expected'] for v in recognition)
            for right in bars:
                if right['background']!=m['target_background']:continue
                a,b,c,d=left['box'];r,k,R,K=right['box']
                if (c-a,d-b)!=(R-r,K-k):continue
                if not (b+d==k+K or a+c==r+R):continue
                actual=glyphs(right)
                if len(actual)!=len(expected):continue
                mismatches=[i for i,(g,e) in enumerate(zip(actual,expected)) if g['mask']!=e]
                proposals.append(dict(kind='visual_symbol_substitution',source_box=left['box'],target_box=right['box'],source_background=m['source_background'],target_background=m['target_background'],
                    expected=expected,actual=tuple(g['mask'] for g in actual),points=tuple(g['point'] for g in actual),mismatches=mismatches,examples=m['examples'],
                    observation=proof,recognition=recognition,orientation_assumption='Symbol identity may be invariant to rotation/reflection; target orientation follows the observed example. Equivariant alternatives are retained but not selected.',scope='Observed pairs and dihedral shape recognition propose a correspondence. Orientation semantics, direction, editable region, completion and control effects remain unverified hypotheses.'))
    return dict(rectangles=rects,maps=maps,proposals=proposals)
