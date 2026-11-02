"""Infer visual symbol-to-word dictionaries and compose new query sequences."""
from collections import defaultdict
from panel_hypotheses_v2 import rectangles,normalized,transformed,digest

def glyphs(rect):
    a,b,c,d=rect['box'];h=c-a+1;w=d-b+1;pitch=min(h,w)
    if max(h,w)%pitch:return []
    out=[]
    for i in range(max(h,w)//pitch):
        y=a+i*pitch if h>w else a;x=b+i*pitch if w>=h else b
        ink=[p for p in rect['ink'] if y<p[0]<y+pitch-1 and x<p[1]<x+pitch-1]
        if not ink:return []
        out.append(dict(mask=normalized(ink),point=(x+pitch//2,y+pitch//2)))
    return out

def recognize(mask,mapping):
    words={word for source,word in mapping.items() for k in range(4) for f in (False,True) if transformed(source,k,f)==mask}
    return next(iter(words)) if len(words)==1 else None

def candidates(obs,remembered=()):
    proof=digest(obs);rects=[r for r in rectangles(obs['frame']) if glyphs(r)];singles=[i for i,r in enumerate(rects) if len(glyphs(r))==1 and r['box'][2]-r['box'][0]==r['box'][3]-r['box'][1]]
    def gap(r,q):
        if r['background']==q['background']:return None
        a,b,c,d=r['box'];y,x,Y,X=q['box'];options=[]
        if a+c==y+Y and c-a==Y-y:
            if d<x:options.append(x-d-1)
            if X<b:options.append(b-X-1)
        if b+d==x+X and d-b==X-x:
            if c<y:options.append(y-c-1)
            if Y<a:options.append(a-Y-1)
        return min(options) if options else None
    nearest={}
    for i,r in enumerate(rects):
        distances=[(gap(r,q),j) for j,q in enumerate(rects) if j!=i and gap(r,q) is not None]
        if distances:
            best=min(d for d,j in distances);nearest[i]={j for d,j in distances if d==best}
    groups=defaultdict(list)
    for i in singles:
        r=rects[i]
        for j in sorted(nearest.get(i,())):
            if i not in nearest.get(j,()):continue
            q=rects[j];groups[r['background'],q['background']].append(dict(source_mask=glyphs(r)[0]['mask'],target_masks=tuple(g['mask'] for g in glyphs(q)),source_box=r['box'],target_box=q['box'],observation=proof))
    maps=[]
    for (left,right),examples in sorted(groups.items()):
        mapping=defaultdict(set)
        for e in examples:mapping[e['source_mask']].add(e['target_masks'])
        if len(mapping)<3 or any(len(v)!=1 for v in mapping.values()):continue
        maps.append(dict(source_background=left,target_background=right,mapping={k:next(iter(v)) for k,v in mapping.items()},examples=examples))
    dictionaries=maps if maps else list(remembered);proposals=[]
    for m in dictionaries:
        for left in rects:
            source=glyphs(left)
            if left['background']!=m['source_background'] or len(source)<2:continue
            words=[recognize(g['mask'],m['mapping']) for g in source]
            if any(word is None for word in words):continue
            expected=tuple(mask for word in words for mask in word)
            for right in rects:
                if right['background']!=m['target_background']:continue
                a,b,c,d=left['box'];y,x,Y,X=right['box'];h=c-a+1;w=d-b+1;H=Y-y+1;W=X-x+1
                aligned=(w>h and W>H and h==H and abs(b+d-x-X)<=1) or (h>w and H>W and w==W and abs(a+c-y-Y)<=1)
                actual=glyphs(right)
                if not aligned or len(actual)!=len(expected):continue
                proposals.append(dict(kind='visual_symbol_word_substitution',source_box=left['box'],target_box=right['box'],source_background=m['source_background'],target_background=m['target_background'],expected=expected,actual=tuple(g['mask'] for g in actual),examples=m['examples'],observation=proof,
                    scope='Tentative concatenation of observed symbol-to-word mappings, including unequal lengths. Equal visual cell lattice and orientation-invariant identity remain hypotheses; actual progress determines sufficiency.'))
    return dict(rectangles=rects,maps=maps,proposals=proposals)
