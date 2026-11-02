"""Retain observed object transport and counterexamples to body passability.

Transport is an observational subgoal hypothesis, not a causal guarantee.
No color, direction, action number or public coordinate has a predefined role.
"""
from collections import Counter
from itertools import permutations

def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def feature(frame,p,n):
    y,x=p
    if y<0 or x<0 or y+n>len(frame) or x+n>len(frame[0]):return None
    return tuple(sorted(Counter(frame[a][b] for a in range(y,y+n) for b in range(x,x+n)).items()))

def correspondence(left,right):
    if not left or len(left)!=len(right) or len(left)>7:return None
    ranked=[]
    for perm in permutations(range(len(right))):
        if any(tuple(a['box'][2:])!=tuple(right[j]['box'][2:]) or a['inner_ink']!=right[j]['inner_ink'] for a,j in zip(left,perm)):continue
        cost=sum(sum(abs(a['box'][k]-right[j]['box'][k]) for k in (0,1)) for a,j in zip(left,perm))
        ranked.append((cost,perm))
    ranked.sort()
    if not ranked or len(ranked)>1 and ranked[0][0]==ranked[1][0]:return None
    return list(zip(left,[right[j] for j in ranked[0][1]]))

class Memory:
    def __init__(self):
        self.paths={};self.transports=[];self.blocked={};self.passed={};self.last_level=None
    def boundary(self,level,forget=False):
        self.paths={}
        if forget:self.transports=[];self.blocked={};self.passed={}
        self.last_level=level
    def observe(self,before,after,left,right,body_before,body_after,action,t,motions,goal_slots,held):
        level=before['levels_completed'];n=body_before['box'][2]
        if before['state']!=after['state'] or before['state']!='NOT_FINISHED' or level!=after['levels_completed']:
            self.boundary(after['levels_completed']);return
        p=tuple(body_before['box'][:2]);q=tuple(body_after['box'][:2]);delta=sub(q,p)
        if action in motions:
            expected=add(p,motions[action]['delta']);look=feature(before['frame'],expected,n)
            cargo={tuple(z['box'][:2]) for z in left}
            if look is not None and len(look)>1 and expected not in cargo:
                key=(level,look)
                if q==expected:self.passed.setdefault(key,[]).append(t)
                elif q==p:
                    # Do not label a body surface from a held-object collision.
                    held_next=None if held is None else add(expected,held)
                    if held_next is None or held_next not in cargo:
                        self.blocked.setdefault(key,[]).append((t,expected))
        pairs=correspondence(left,right);next_paths={}
        if pairs is None:self.paths={};return
        for a,b in pairs:
            start=tuple(a['box'][:2]);end=tuple(b['box'][:2]);movement=sub(end,start)
            key=(start,a['inner_ink'],tuple(a['box'][2:]));old=self.paths.get(key)
            is_held=held is not None and start==add(p,held)
            distant=sum(abs(start[k]-p[k]) for k in (0,1))>2*n
            if is_held:continue
            if movement!=(0,0):
                if old is None:
                    old=dict(level=level,start=start,first=t,steps=[],far_steps=[],last=end)
                old={**old,'steps':old['steps']+[t], 'far_steps':old['far_steps']+([t] if distant else []),'last':end}
                next_paths[(end,b['inner_ink'],tuple(b['box'][2:]))]=old
            elif old and old['steps'] and old['steps'][-1]==t-1:
                if end in goal_slots and len(old['steps'])>=2 and len(old['far_steps'])>=2 and old['start'] not in goal_slots:
                    record=dict(level=level,start=old['start'],end=end,first=old['first'],last=t,
                                moves=list(old['steps']),far_steps=list(old['far_steps']))
                    if not any(r['level']==level and r['start']==old['start'] for r in self.transports):self.transports.append(record)
                # A stopped track must not be joined to a later unrelated move.
        self.paths=next_paths
    def barriers(self,level):
        return [(look,values) for (lev,look),values in self.blocked.items()
                if lev==level and len({p for _,p in values})>=2 and not self.passed.get((lev,look))]
    def entries(self,level):return {tuple(v['start']) for v in self.transports if v['level']==level}
