"""Infer orthogonal, diagonal and diamond line figures from visible color support."""
from collections import Counter

def shape_points(center,geom):
    y,x=center;r=geom['radius'];kind=geom['kind']
    if kind=='plus':return {(y+d,x) for d in range(-r[0],r[0]+1)}|{(y,x+d) for d in range(-r[1],r[1]+1)}
    if kind=='diagonal':return {(y+d,x+d) for d in range(-r,r+1)}|{(y+d,x-d) for d in range(-r,r+1)}
    if kind=='diamond':return {(y+d,x+s*(r-abs(d))) for d in range(-r,r+1) for s in [-1,1]}
    raise ValueError(kind)
def covers(center,geom,targets):return bool(targets) and set(map(tuple,targets))<=shape_points(center,geom)
def scene(obs):
    f=obs['frame'];totals=Counter(v for row in f for v in row);bg=totals.most_common(1)[0][0];targets={}
    for y in range(1,61):
        for x in range(1,63):
            c=f[y][x]
            if c==bg:continue
            ring=[f[y+a][x+b] for a in (-1,0,1) for b in (-1,0,1) if a or b]
            if len(set(ring))==1 and ring[0] not in (bg,c):targets.setdefault(c,[]).append((y,x))
    out={}
    for c in sorted(set(totals)-{bg}):
        ps={(y,x) for y,row in enumerate(f[:62]) for x,v in enumerate(row) if v==c}-set(targets.get(c,[]))
        if len(ps)<20:continue
        ys=Counter(y for y,x in ps);xs=Counter(x for y,x in ps);ds=Counter(y-x for y,x in ps);ss=Counter(y+x for y,x in ps);candidates=[]
        y=max(ys,key=lambda y:(ys[y],-y));x=max(xs,key=lambda x:(xs[x],-x))
        if ys[y]>=9 and xs[x]>=9:
            h=[b for a,b in ps if a==y];v=[a for a,b in ps if b==x];candidates.append(((y,x),dict(kind='plus',radius=(max(y-min(v),max(v)-y),max(x-min(h),max(h)-x)))))
        d=ds.most_common(2);s=ss.most_common(2)
        if d[0][1]>=9 and s[0][1]>=9 and (d[0][0]+s[0][0])%2==0:
            y=(d[0][0]+s[0][0])//2;x=(s[0][0]-d[0][0])//2;r=max(abs(a-y) for a,b in ps if a-b==d[0][0] or a+b==s[0][0]);candidates.append(((y,x),dict(kind='diagonal',radius=r)))
        if len(d)>=2 and len(s)>=2 and min(d[1][1],s[1][1])>=5:
            dp=sorted(q[0] for q in d);sp=sorted(q[0] for q in s)
            if dp[1]-dp[0]==sp[1]-sp[0] and (sum(dp)+sum(sp))%4==0 and (sum(sp)-sum(dp))%4==0:
                y=(sum(dp)+sum(sp))//4;x=(sum(sp)-sum(dp))//4;r=(dp[1]-dp[0])//2;candidates.append(((y,x),dict(kind='diamond',radius=r)))
        scored=[]
        for center,g in candidates:
            y,x=center
            if not(0<=y<62 and 0<=x<64):continue
            points=shape_points(center,g);coverage=len(points&ps)/len(ps);visible={p for p in points if 0<=p[0]<62 and 0<=p[1]<64};fit=len(visible&ps)/len(visible)
            if coverage>=.75 and fit>=.65:scored.append((coverage+fit,center,g))
        if scored:
            _,center,g=max(scored,key=lambda q:(q[0],str(q[2])));v=f[center[0]][center[1]];out[c]=dict(center=center,radius=g,selected=v not in (bg,c) and totals[v]<=4)
    return out,{c:targets.get(c,[]) for c in out}
