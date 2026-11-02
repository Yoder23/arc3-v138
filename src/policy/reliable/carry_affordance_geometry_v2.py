"""Visible framed motifs and striped square bodies; roles remain hypotheses."""
from collections import Counter
from cyclic_perimeter_geometry_v1 import inventory

def scene(frame):
    height=len(frame);width=len(frame[0]);bg=Counter(v for row in frame for v in row).most_common(1)[0][0]
    framed=[];bodies=[];items=inventory(frame)
    # The older general-purpose inventory suppresses singleton components.
    # Small framed symbols can legitimately have a one-pixel center.
    for y,row in enumerate(frame):
        for x,ink in enumerate(row):
            if ink==bg:continue
            if all(not (0<=a<height and 0<=b<width) or frame[a][b]!=ink for a,b in ((y-1,x),(y+1,x),(y,x-1),(y,x+1))):
                items.append(dict(box=(y,x,1,1),ink=ink,area=1))
    for item in items:
        y,x,h,w=item['box'];ink=item['ink']
        if item['area']!=h*w:continue
        if 1<=h<=24 and 1<=w<=24 and y>0 and x>0 and y+h<height and x+w<width:
            border={(y-1,c) for c in range(x-1,x+w+1)}|{(y+h,c) for c in range(x-1,x+w+1)}|{(a,x-1) for a in range(y,y+h)}|{(a,x+w) for a in range(y,y+h)}
            values={frame[a][b] for a,b in border}
            if len(values)==1 and ink not in values and bg not in values:
                framed.append(dict(box=(y-1,x-1,h+2,w+2),inner_ink=ink,frame_ink=next(iter(values)),inner_box=item['box']))
        n=max(h,w)
        if not 3<=n<=8 or min(h,w)!=n-1:continue
        options=[((y-1,x,n,n),[(y-1,c) for c in range(x,x+w)]),((y,x,n,n),[(y+h,c) for c in range(x,x+w)])] if h<w else [((y,x-1,n,n),[(a,x-1) for a in range(y,y+h)]),((y,x,n,n),[(a,x+w) for a in range(y,y+h)])]
        for box,strip in options:
            if any(a<0 or b<0 or a>=height or b>=width for a,b in strip):continue
            values={frame[a][b] for a,b in strip}
            if len(values)==1 and bg not in values and ink not in values:
                bodies.append(dict(box=box,fill_ink=ink,stripe_ink=next(iter(values)),fill_box=item['box']))
    multiplicity=Counter((v['box'][2:],v['inner_ink']) for v in framed)
    cargo=[v for v in framed if v['box'][2]==v['box'][3] and multiplicity[v['box'][2:],v['inner_ink']]>=2]
    containers=[]
    for v in framed:
        if any(v['box'][2]%c['box'][2]==0 and v['box'][3]%c['box'][3]==0 and v['box'][2]*v['box'][3]>=2*c['box'][2]*c['box'][3] for c in cargo):containers.append(v)
    return dict(bodies=bodies,cargo=cargo,containers=containers,framed=framed)
