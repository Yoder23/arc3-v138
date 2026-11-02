"""Infer periodic positions from repeated visible control observations, retaining occlusion."""
from collections import defaultdict
from collections import deque
from math import lcm
def learn(history,models,controls,t):
    by=defaultdict(list)
    for c in controls:by[c['signature']].append(c)
    for sig,items in by.items():
        if len(items)!=1:continue
        h=history.setdefault(sig,{});h[t]=items[0]['box']
        if len(set(h.values()))<2:continue
        recent={k:v for k,v in h.items()if k>=t-64}
        for p in range(2,17):
            phases=defaultdict(list)
            for k,v in recent.items():phases[k%p].append(v)
            if len(phases)==p and all(len(v)>=2 and len(set(v))==1 for v in phases.values()):
                models[sig]=dict(period=p,positions=tuple(phases[k][0]for k in range(p)),sources=tuple(sorted(recent)));break
        else:models.pop(sig,None)
def at(control,models,t):
    m=models.get(control['signature'])
    return dict(control,box=m['positions'][t%m['period']])if m else control
def refresh(retained,visible,models,t,actor):
    dynamic=set(models);out=[]
    for c in retained:
        if c['signature']in dynamic:
            if not any(v['signature']==c['signature']for v in out):out.append(at(c,models,t))
        elif c not in out:out.append(c)
    for c in visible:
        if c['signature']in dynamic:
            out=[v for v in out if v['signature']!=c['signature']];out.append(c)
        elif not any(v['box']==c['box']for v in out):out.append(c)
    return out
def intercept(pos,control,mask,n,controls,motion,clocks,t,stationary_rejected=False):
    period=lcm(*[m['period']for m in clocks.values()])if clocks else 1
    def cover(p,c):
        y,x,h,w=c['box'];return p[0]<=y+h//2<p[0]+n and p[1]<=x+w//2<p[1]+n
    queue=deque([(pos,t%period,[])]);seen={(pos,t%period)}
    while queue:
        p,phase,path=queue.popleft()
        for action,(dy,dx)in {1:(-1,0),2:(1,0),3:(0,-1),4:(0,1)}.items():
            q=motion.get((p,action,n),(p[0]+dy*n,p[1]+dx*n));nextphase=(phase+1)%period
            if not all((y,x)in mask for y in range(q[0],q[0]+n)for x in range(q[1],q[1]+n)):q=p
            if stationary_rejected and q==p:continue
            if cover(q,at(control,clocks,phase+1))and not cover(p,at(control,clocks,phase)):return path+[action]
            if any(c['signature']!=control['signature']and cover(q,at(c,clocks,phase+1))and not cover(p,at(c,clocks,phase))for c in controls):continue
            if(q,nextphase)not in seen:seen.add((q,nextphase));queue.append((q,nextphase,path+[action]))
    return None
