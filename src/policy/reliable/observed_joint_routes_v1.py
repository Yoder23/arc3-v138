"""Plan with measured joint transitions; keep unmeasured edges hypothetical."""
from collections import deque

def state(body,cargo):return (tuple(body),tuple(sorted(tuple(p) for p in cargo)))
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))

class Memory:
    def __init__(self):
        self.edges={};self.dynamic=False
    def observe(self,before,action,after,support,offset=None):
        assert type(action) is int and type(support) is int and support>=0
        outcomes=self.edges.setdefault((before,action),{})
        outcomes.setdefault(after,support)
        old=set(before[1]);expected=set(old)
        if offset is not None:
            expected.discard(add(before[0],offset));expected.add(add(after[0],offset))
        if set(after[1])!=expected:self.dynamic=True
    def witnesses(self):return sorted({i for values in self.edges.values() for i in values.values()})
    def observed(self,s,action):
        values=self.edges.get((s,action))
        if values and len(values)==1:
            next_state=next(iter(values));return next_state,values[next_state]
        return None
    def route(self,start,target,motions,n,offset=None,blocked=(),limit=2500):
        todo=deque([start]);previous={start:None};found=None
        while todo and len(previous)<limit:
            current=todo.popleft();p,cargo=current
            if p==tuple(target):found=current;break
            for action,delta in sorted(motions.items()):
                values=self.edges.get((current,action))
                if values:
                    # Conflicting actual outcomes refute determinism in this
                    # representation. Do not select one convenient outcome.
                    if len(values)!=1:continue
                    nxt=next(iter(values))
                else:
                    q=add(p,delta);loose=set(cargo)
                    if offset is not None:loose.discard(add(p,offset))
                    held=None if offset is None else add(q,offset)
                    if q in loose or not all(0<=x<=64-n for x in q):continue
                    if held is not None and (held in loose or not all(0<=x<=64-n for x in held)):continue
                    if (p,action,tuple(sorted(start[1]))) in blocked:continue
                    nxt=state(q,loose if held is None else loose|{held})
                if nxt in previous:continue
                previous[nxt]=(current,action);todo.append(nxt)
        if found is None:return None
        actions=[]
        while previous[found] is not None:found,a=previous[found];actions.append(a)
        return actions[::-1]
