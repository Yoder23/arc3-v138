"""Cheap optimistic feasibility checks before joint symbol/resource search."""
from collections import deque

def possible(scene,mask,controls,rules,shapes,colors,motion,clocks,goal_contact,covers,transform,DIRS):
    n=scene['actor'][2];start=scene['actor'][:2];reachable={start};todo=deque([start])
    while todo:
        p=todo.popleft()
        for a,(dy,dx)in DIRS.items():
            q=motion.get((p,a,n),(p[0]+dy*n,p[1]+dx*n))
            if q not in reachable and all((y,x)in mask for y in range(q[0],q[0]+n)for x in range(q[1],q[1]+n)):
                reachable.add(q);todo.append(q)
    g=scene['goal'];target=(g[0]+(g[2]-n)//2,g[1]+(g[3]-n)//2)
    if goal_contact and target not in reachable:return False
    available=[]
    for c in controls:
        model=clocks.get(c['signature']);positions=model['positions']if model else[c['box']]
        if any(covers(p,n,dict(c,box=box))for p in reachable for box in positions):available.append(c)
    start=(scene['key'],scene['key_color']);wanted=(scene['target'],scene['target_color']);todo=deque([start]);seen={start}
    while todo and len(seen)<4096:
        key,color=todo.popleft()
        if(key,color)==wanted:return True
        for c in available:
            sig=c['signature'];ops=rules.get(sig);newkey=shapes.get(sig,{}).get(key,transform(key,min(ops)if ops else 0));newcolor=colors.get(sig,{}).get(color,color);state=(newkey,newcolor)
            if state not in seen:seen.add(state);todo.append(state)
    # A saturated abstraction is inconclusive; retain the original search.
    return bool(todo)
