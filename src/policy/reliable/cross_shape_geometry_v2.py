"""Decompose several same-color line figures by supported geometric templates."""
from collections import Counter
from itertools import combinations,product
from cross_shape_geometry_v1 import scene as prior_scene,shape_points as old_points

def shape_points(center,g):
    y,x=center
    if g['kind']=='horizontal':return {(y,x+d) for d in range(-g['radius'],g['radius']+1)}
    if g['kind']=='vertical':return {(y+d,x) for d in range(-g['radius'],g['radius']+1)}
    return old_points(center,g)
def scene(obs):
    f=obs['frame'];totals=Counter(v for row in f for v in row);bg=totals.most_common(1)[0][0];targets={};out={}
    for y in range(1,61):
        for x in range(1,63):
            c=f[y][x];ring={f[y+a][x+b] for a in [-1,0,1] for b in [-1,0,1] if a or b}
            if c!=bg and len(ring)==1 and c not in ring and bg not in ring:targets.setdefault(c,[]).append((y,x))
    simple,_=prior_scene(obs)
    for c in sorted(set(totals)-{bg}):
        ps={(y,x) for y,row in enumerate(f[:62]) for x,v in enumerate(row) if v==c}-set(targets.get(c,[]))
        if len(ps)<17:continue
        candidates=[]
        def add(center,g):
            y,x=center
            if not(0<=y<62 and 0<=x<64):return
            pts={p for p in shape_points(center,g) if 0<=p[0]<62 and 0<=p[1]<64};supported=pts&ps
            if len(pts)>=17 and len(supported)>=.78*len(pts):candidates.append((len(supported),center,g,pts))
        if c in simple:add(simple[c]['center'],simple[c]['radius'])
        rows=Counter(y for y,x in ps);cols=Counter(x for y,x in ps);ds=Counter(y-x for y,x in ps);ss=Counter(y+x for y,x in ps)
        for axis,groups in [(0,rows),(1,cols)]:
            for k,n in groups.items():
                if n<17:continue
                values=sorted(p[1-axis] for p in ps if p[axis]==k);runs=[];run=[]
                for v in values:
                    if run and v-run[-1]>2:runs.append(run);run=[]
                    run.append(v)
                if run:runs.append(run)
                for run in runs:
                    if run[-1]-run[0]<16 or (run[-1]+run[0])%2:continue
                    center=(k,(run[0]+run[-1])//2) if axis==0 else ((run[0]+run[-1])//2,k);add(center,dict(kind='horizontal' if axis==0 else 'vertical',radius=(run[-1]-run[0])//2))
        diagonals=[d for d,n in ds.items() if n>=7];sums=[s for s,n in ss.items() if n>=7]
        for d,s in product(diagonals,sums):
            if (d+s)%2:continue
            y=(d+s)//2;x=(s-d)//2;on1=[a for a,b in ps if a-b==d];on2=[a for a,b in ps if a+b==s];r=min(max(abs(a-y) for a in on1),max(abs(a-y) for a in on2))
            if 4<=r<=30:add((y,x),dict(kind='diagonal',radius=r))
        for dp in combinations(diagonals,2):
            for sp in combinations(sums,2):
                if abs(dp[1]-dp[0])!=abs(sp[1]-sp[0]) or (sum(dp)+sum(sp))%4 or (sum(sp)-sum(dp))%4:continue
                r=abs(dp[1]-dp[0])//2
                if 4<=r<=30:add(((sum(dp)+sum(sp))//4,(sum(sp)-sum(dp))//4),dict(kind='diamond',radius=r))
        remaining=set(ps);selected=[]
        while candidates and len(selected)<6:
            best=max(candidates,key=lambda q:(len(q[3]&remaining),q[0],str(q[2])));candidates.remove(best);n,center,g,pts=best;new=len(pts&remaining)
            if new<12 or new<.5*len(pts):continue
            selected.append((center,g));remaining-=pts
        for center,g in selected:
            key=str((c,g['kind'],g['radius']));v=f[center[0]][center[1]]
            if key in out:out.pop(key);continue
            out[key]=dict(color=c,center=center,radius=g,selected=v not in (bg,c) and totals[v]<=4)
    return out,targets
