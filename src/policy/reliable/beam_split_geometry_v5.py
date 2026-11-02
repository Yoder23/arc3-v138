"""Visible splitter, emitter and open-cup hypotheses; no stored layouts."""
from collections import Counter,deque
from beam_motion_constraints_v1 import allowed
from binary_demonstration_bootstrap_v1 import components
def perceive(frame):
    obs=components(frame);bars=[o for o in obs if len(o['shape'])==o['box'][2]*o['box'][3]and 3<=min(o['box'][2:])<=8 and max(o['box'][2:])>=3*min(o['box'][2:])and max(o['box'][2:])<=7*min(o['box'][2:])and o['box'][0]>0]
    if not bars:return None
    sizes=Counter(min(o['box'][2:])for o in bars);n=sizes.most_common(1)[0][0];bars=[o for o in bars if min(o['box'][2:])==n]
    goals=[]
    for o in obs:
        y,x,h,w=o['box']
        if sorted((h,w))!=[2*n,3*n]or len(o['shape'])!=5*n*n:continue
        cells=set(o['shape']);holes=[]
        for yy in range(0,h,n):
            for xx in range(0,w,n):
                if all((dy,dx)not in cells for dy in range(yy,yy+n)for dx in range(xx,xx+n)):holes.append((y+yy,x+xx))
        if len(holes)==1:goals.append(dict(object=o,opening=holes[0]))
    if not goals:return None
    sources=[]
    for o in obs:
        y,x,h,w=o['box']
        if(h,w)!=(n,n)or len(o['shape'])!=n*n:continue
        for q in obs:
            yy,xx,hh,ww=q['box']
            if q==o or len(q['shape'])!=hh*ww:continue
            direction=None
            if x==xx and w==ww and hh<=n:
                if yy+hh==y:direction=(1,0)
                elif y+h==yy:direction=(-1,0)
            elif y==yy and h==hh and ww<=n:
                if xx+ww==x:direction=(0,1)
                elif x+w==xx:direction=(0,-1)
            distance=min(y,x,64-y-h,64-x-w);other_distance=min(yy,xx,64-yy-hh,64-xx-ww)
            if direction and other_distance<distance<=2*n:sources.append(dict(object=o,companion=q,position=(y,x),direction=direction))
    if not sources or len({v["direction"]for v in sources})!=1:return None
    source=sources[0];axis=0 if source['direction'][0]else 1
    bars=[o for o in bars if o['box'][axis+2]==n and all(v%n==0 for v in o['box'][2:])]
    if not bars:return None
    bars.sort(key=lambda o:(o['box'][2:],o['box'][:2]))
    origin=tuple(v%n for v in bars[0]['box'][:2])
    if any(tuple(v%n for v in b['box'][:2])!=origin for b in bars):return None
    return dict(origin=origin,n=n,bars=bars,goals=goals,source=source,sources=sources,axis=axis,background=Counter(v for row in frame[1:-1]for v in row).most_common(1)[0][0])
def trace(s,poses):
    n=s['n'];dy,dx=s['source']['direction'];queue=deque([v['position']for v in s['sources']]);seen=set();hits=set();misses=set();rays=set();splits=[]
    while queue and len(seen)<1024:
        y,x=queue.popleft();y+=dy*n;x+=dx*n
        if not(0<=y<64 and 0<=x<64)or(y,x)in seen:continue
        seen.add((y,x));rays.add((y,x));caught=False
        for i,g in enumerate(s['goals']):
            gy,gx,h,w=g['object']['box']
            if gy<=y<gy+h and gx<=x<gx+w:
                (hits if (y,x)==tuple(g['opening'])else misses).add(i);caught=True;break
        if caught:continue
        for i,(yy,xx)in enumerate(poses):
            h,w=s['bars'][i]['box'][2:]
            if yy<=y<yy+h and xx<=x<xx+w:
                if dy:children=[(y-dy*n,xx-n),(y-dy*n,xx+w)]
                else:children=[(yy-n,x-dx*n),(yy+h,x-dx*n)]
                queue.extend(children);splits.append(dict(index=i,entry=(y,x),children=children));caught=True;break
        if not caught:queue.append((y,x))
    return dict(hits=sorted(hits),misses=sorted(misses),rays=sorted(rays),splits=splits)
def overlap(a,b):
    y,x,h,w=a;yy,xx,hh,ww=b;return y<yy+hh and yy<y+h and x<xx+ww and xx<x+w
def valid(s,poses):
    boxes=[(*p,*b['box'][2:])for p,b in zip(poses,s['bars'])]
    forbidden=[g['object']['box']for g in s['goals']]+[z[k]['box']for z in s['sources']for k in ('object','companion')]
    return not any(overlap(a,b)for i,a in enumerate(boxes)for b in boxes[i+1:]+forbidden)
def plan(s,failed,depth=4,width=16,limits=None,groups=None):
    limits=limits or {};groups=groups or[(i,)for i in range(len(s['bars']))]
    start=tuple(b['box'][:2]for b in s['bars']);n=s['n'];seen={start};beam=[start];best=None
    def rank(state):
        result=trace(s,state);distance=sum(abs(a-b)for p,q in zip(start,state)for a,b in zip(p,q))//n
        return (-len(result['hits']),len(result['misses']),distance,len(result['splits']),state)
    for _ in range(depth+1):
        ranked=sorted((rank(q),q)for q in beam)
        viable=[v for v in ranked if v[1]not in failed]
        if viable and viable[0][0][0]==-len(s['goals']):return viable[0][1]
        if viable and(best is None or viable[0][0]<best[0]):best=viable[0]
        next_states=[]
        for state in [q for _,q in ranked[:width]]:
            for i,b in enumerate(s['bars']):
                group=next(g for g in groups if i in g)
                if i!=group[0]:continue
                h,w=b['box'][2:]
                for y in range(s['origin'][0]or n,64-h+1,n):
                    for x in range(s['origin'][1],64-w+1,n):
                        delta=(y-state[i][0],x-state[i][1]);dest=tuple((p[0]+delta[0],p[1]+delta[1])if j in group else p for j,p in enumerate(state))
                        if any(not(0<=q[0]<=64-s['bars'][j]['box'][2]and 0<=q[1]<=64-s['bars'][j]['box'][3])or not allowed(j,q,limits)for j,q in enumerate(dest)):continue
                        if dest in seen or not allowed(i,(y,x),limits):continue
                        seen.add(dest)
                        if valid(s,dest):next_states.append(dest)
        beam=next_states
        if not beam:break
    return best[1]if best else None
