"""Canonical rectangular outlines and scaled three-by-three body patterns."""
from collections import defaultdict

def body_crop(frame,box,ink,allow_partial=False):
    y,x,h,w=box
    if h%3 or w%3 or not(3<=h<=12 and 3<=w<=12 and 0<=y<=64-h and 0<=x<=64-w):return None
    sy,sx=h//3,w//3;values=[]
    for row in range(3):
        for col in range(3):
            vals={frame[yy][xx] for yy in range(y+row*sy,y+(row+1)*sy) for xx in range(x+col*sx,x+(col+1)*sx)}
            if len(vals)!=1:return None
            values.append(next(iter(vals)))
    center=values[4];border=values[:4]+values[5:]
    if center==ink or any(v not in (ink,center) for v in border):return None
    count=border.count(ink)
    if count!=8 and not(allow_partial and count>=5):return None
    return dict(box=tuple(box),ink=ink,center=center,tile_body=True,visible_border_tiles=count)

def rings(frame):
    seen=set();out=[]
    for y in range(64):
        for x in range(64):
            if (y,x) in seen:continue
            ink=frame[y][x];stack=[(y,x)];seen.add((y,x));cells=[]
            while stack:
                a,b=stack.pop();cells.append((a,b))
                for q in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
                    if 0<=q[0]<64 and 0<=q[1]<64 and q not in seen and frame[q[0]][q[1]]==ink:seen.add(q);stack.append(q)
            yy=min(a for a,b in cells);xx=min(b for a,b in cells);h=max(a for a,b in cells)-yy+1;w=max(b for a,b in cells)-xx+1
            if not(3<=h<=14 and 3<=w<=14):continue
            center=frame[yy+h//2][xx+w//2]
            if center==ink:continue
            if not(all(frame[yy][b]==frame[yy+h-1][b]==ink for b in range(xx,xx+w)) and all(frame[a][xx]==frame[a][xx+w-1]==ink for a in range(yy,yy+h))):continue
            body=body_crop(frame,(yy,xx,h,w),ink)
            out.append(body or dict(box=(yy,xx,h,w),ink=ink,center=center))
    return sorted(out,key=lambda r:(r['box'][0],r['box'][1],r['box'][2:]))

def actor_group(frame):
    groups=defaultdict(list)
    for r in rings(frame):
        if r.get('tile_body'):groups[r['ink']].append(r)
    choices=[rs for rs in groups.values() if 2<=len(rs)<=4]
    return min(choices,key=lambda rs:(-len(rs),sum(r['box'][2]*r['box'][3] for r in rs),rs[0]['ink'])) if choices else []
