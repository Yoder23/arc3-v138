"""Joint search over heterogeneous body footprints and matching goal interiors."""
import copy,heapq,itertools
from collections import Counter
from selectable_rect_push_core_v2 import Agent as Base,overlap,inside
class Agent(Base):
    def observe(self,raw):
        count=len(self.push_memory);result=super().observe(raw)
        for p in self.push_memory[count:]:p['actor_after']=copy.deepcopy(next(o for o in self.objects if tuple(o['box'])==tuple(p['actor']['box'])))
        return result
    def joint_plan(self,raw):
        if not 2<=len(self.objects)==len(self.goals)<=4 or len(self.motions)<2:return None
        bodies=sorted(self.objects,key=lambda o:self.identities[tuple(o['box'])]);ids=[self.identities[tuple(o['box'])] for o in bodies];sizes=[tuple(b['box'][2:]) for b in bodies];start=tuple(tuple(o['box'][:2]) for o in bodies)
        choices=[perm for perm in itertools.permutations(self.goals) if all((g['box'][2]-2,g['box'][3]-2)==size for g,size in zip(perm,sizes))]
        if not choices:return None
        perms=[tuple((g['box'][0]+1,g['box'][1]+1) for g in perm) for perm in choices];step=max(abs(v) for m in self.motions.values() for v in m['delta']);floor=self.floor;bg=Counter(raw['frame'][y][x] for y,x in ((0,0),(0,63),(63,0),(63,63))).most_common(1)[0][0]
        allowed=(set(v for row in raw['frame'] for v in row)-{bg,self.palette})|{floor};self.extra_terrain=allowed-{floor}-{g['ink'] for g in self.goals}
        def pattern(q,size):return tuple(floor if any(inside((y,x),b['box']) for b in bodies) else raw['frame'][y][x] for y in range(q[0],q[0]+size[0]) for x in range(q[1],q[1]+size[1]))
        def heuristic(ps):return min(sum(abs(p[0]-g[0])+abs(p[1]-g[1]) for p,g in zip(ps,perm)) for perm in perms)/step
        active=next((i for i,b in enumerate(bodies) if tuple(b['box'])==tuple(self.active_box or ())),0);key=(start,active);todo=[(heuristic(start),0,0,key)];cost={key:0};parents={key:None};serial=0;expanded=0;tie_direction=-1 if len(bodies)>2 else 1
        while todo and expanded<16000:
            _,tie_value,_,state=heapq.heappop(todo);g=tie_value*tie_direction
            if g!=cost[state]:continue
            ps,selected=state;expanded+=1
            if ps in perms:
                moves=[]
                while parents[state] is not None:prev,i,a=parents[state];moves.append((i,a));state=prev
                self.joint_diagnostics.append(dict(source=self.t,expanded=expanded,found=True));return bodies,moves[::-1]
            for i,pos in enumerate(ps):
                h,w=sizes[i]
                for a,m in sorted(self.motions.items()):
                    dy,dx=m['delta'];q=pos[0]+dy,pos[1]+dx
                    if not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
                    colliders=[j for j,other in enumerate(ps) if i!=j and overlap((*q,h,w),(*other,*sizes[j]))];dest=list(ps)
                    if colliders:
                        if len(colliders)!=1 or not self.push_memory or self.disable_push:continue
                        j=colliders[0];pushed=ps[j][0]+dy,ps[j][1]+dx;hh,ww=sizes[j]
                        if not(0<=pushed[0]<=64-hh and 0<=pushed[1]<=64-ww):continue
                        if any(overlap((*pushed,hh,ww),(*other,*sizes[k])) for k,other in enumerate(ps) if k!=j):continue
                        pat=pattern(pushed,sizes[j])
                        if any(v not in allowed for v in pat):continue
                        if any(c['identity']==ids[j] and tuple(c['delta'])==(dy,dx) and tuple(c['pattern'])==pat for c in self.push_constraints):continue
                        dest[j]=pushed
                    else:
                        pat=pattern(q,sizes[i])
                        if any(v not in allowed for v in pat):continue
                        if any(c['identity']==ids[i] and tuple(c['delta'])==(dy,dx) and tuple(c['pattern'])==pat for c in self.constraint_hypotheses):continue
                        dest[i]=q
                    k=(tuple(dest),i);gg=g+1+(i!=selected)
                    if gg>=cost.get(k,10**9):continue
                    cost[k]=gg;parents[k]=(state,i,a);serial+=1;heapq.heappush(todo,(gg+heuristic(k[0]),gg*tie_direction,serial,k))
        self.joint_diagnostics.append(dict(source=self.t,expanded=expanded,found=False,limit_reached=bool(todo)));return None
