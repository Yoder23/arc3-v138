"""Visual priors for uniformly spaced perimeter tokens and corner markers."""
from collections import Counter,defaultdict
from visual_transform_learner import parts

def inventory(frame):
    out=[]
    for ink,shape,(y,x) in parts(frame):
        h=max(v for v,u in shape)+1;w=max(u for v,u in shape)+1
        out.append(dict(box=(y,x,h,w),ink=ink,area=len(shape),shape=shape))
    return out

def perimeter(y,x,h,w,pitch,size):
    return tuple([(y,x+i*pitch,size,size) for i in range(w)]
        +[(y+i*pitch,x+(w-1)*pitch,size,size) for i in range(1,h)]
        +[(y+(h-1)*pitch,x+i*pitch,size,size) for i in range(w-2,-1,-1)]
        +[(y+i*pitch,x,size,size) for i in range(h-2,0,-1)])

def parse(frame):
    items=inventory(frame);squares=defaultdict(dict)
    for item in items:
        y,x,h,w=item['box']
        if 2<=h==w<=5 and item['area']==h*w:squares[h][y,x]=item['ink']
    out=[]
    for size,cells in squares.items():
        rows=defaultdict(list)
        for y,x in cells:rows[y].append(x)
        rows={y:tuple(sorted(xs)) for y,xs in rows.items() if 3<=len(xs)<=10}
        for y,xs in rows.items():
            pitch=xs[1]-xs[0]
            if pitch<=size or any(b-a!=pitch for a,b in zip(xs,xs[1:])):continue
            for bottom,other in rows.items():
                if other!=xs or bottom<=y or (bottom-y)%pitch:continue
                height=1+(bottom-y)//pitch
                if not 3<=height<=10:continue
                boxes=perimeter(y,xs[0],height,len(xs),pitch,size)
                if not 8<=len(boxes)<=32 or any((v,u) not in cells for v,u,h,w in boxes):continue
                out.append(dict(boxes=boxes,word=tuple(cells[v,u] for v,u,h,w in boxes),pitch=pitch,size=size))
    return sorted(out,key=lambda g:(-len(g['boxes']),g['boxes']))

def markers(frame,grid):
    bg=Counter(v for row in frame for v in row).most_common(1)[0][0]
    out=[];H=len(frame);W=len(frame[0])
    for i,(y,x,h,w) in enumerate(grid['boxes']):
        for m in (1,2):
            for gap in (0,1,2):
                boxes=((y-m-gap,x-m-gap,m,m),(y-m-gap,x+w+gap,m,m),
                       (y+h+gap,x-m-gap,m,m),(y+h+gap,x+w+gap,m,m))
                if any(v<0 or u<0 or v+a>H or u+b>W for v,u,a,b in boxes):continue
                vals={frame[v+dv][u+du] for v,u,a,b in boxes for dv in range(a) for du in range(b)}
                if len(vals)==1 and bg not in vals:
                    ink=next(iter(vals))
                    if ink in grid['word']:out.append(dict(index=i,ink=ink,marker_boxes=boxes))
    return out

def controls(frame,grid,goals):
    y0=min(b[0] for b in grid['boxes']);x0=min(b[1] for b in grid['boxes'])
    y1=max(b[0]+b[2] for b in grid['boxes']);x1=max(b[1]+b[3] for b in grid['boxes'])
    blocked={b for g in goals for b in g['marker_boxes']};out=[]
    for item in inventory(frame):
        y,x,h,w=item['box']
        if item['box'] in blocked or not(2<=h<=10 and 2<=w<=10 and 4<=item['area']<=80):continue
        if not(y+h<=y0 or y>=y1 or x+w<=x0 or x>=x1):continue
        out.append(dict(box=item['box'],ink=item['ink'],area=item['area'],shape=item['shape'],
            point=(x+(w-1)//2,y+(h-1)//2)))
    return sorted(out,key=lambda z:(z['box'],z['ink']))

def shifts(before,after):
    if len(before)!=len(after):return ()
    return tuple(k for k in range(len(before)) if tuple(before[k:]+before[:k])==tuple(after))
