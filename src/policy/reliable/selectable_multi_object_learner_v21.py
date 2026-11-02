"""Grounded pair subgoals and observed-success plan continuation for many bodies."""
import copy,heapq,itertools
from collections import Counter
from selectable_multi_object_learner_v20 import Agent as Base
from selectable_rect_push_core_v2 import overlap
from selectable_rect_core_v1 import inside
class Agent(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.pair_plan=None;self.use_subgoals=False;self.pair_diagnostics=[]
    def reset_level(self,raw):super().reset_level(raw);self.pair_plan=None;self.use_subgoals=False;self.pair_diagnostics=[]
    def pair_search(self,raw,target,helper,goal):
        bodies=[target,helper];ids=[self.identities[tuple(b['box'])] for b in bodies];sizes=[tuple(b['box'][2:]) for b in bodies];static=[b for b in self.objects if b is not target and b is not helper];start=tuple(tuple(b['box'][:2]) for b in bodies);finish=(goal['box'][0]+1,goal['box'][1]+1);floor=self.floor
        bg=Counter(raw['frame'][y][x] for y,x in ((0,0),(0,63),(63,0),(63,63))).most_common(1)[0][0];allowed=(set(v for row in raw['frame'] for v in row)-{bg,self.palette})|{floor};step=max(abs(v) for m in self.motions.values() for v in m['delta'])
        def pat(q,size):return tuple(floor if any(inside((y,x),b['box']) for b in self.objects) else raw['frame'][y][x] for y in range(q[0],q[0]+size[0]) for x in range(q[1],q[1]+size[1]))
        def heuristic(ps):return (abs(ps[0][0]-finish[0])+abs(ps[0][1]-finish[1]))/step
        active=next((i for i,b in enumerate(bodies) if tuple(b['box'])==tuple(self.active_box or ())),-1);initial=(start,active);cost={initial:0};parent={initial:None};queue=[(heuristic(start),0,0,initial)];serial=expanded=0
        while queue and expanded<10000:
            _,negative_g,_,state=heapq.heappop(queue);g=-negative_g
            if cost[state]!=g:continue
            ps,selected=state;expanded+=1
            if ps[0]==finish:
                moves=[];states=[];cursor=state
                while parent[cursor] is not None:previous,i,a=parent[cursor];moves.append((ids[i],a));states.append(cursor[0]);cursor=previous
                return dict(ids=ids,moves=moves[::-1],states=states[::-1],before=start,goal=copy.deepcopy(goal),target=ids[0],expanded=expanded,checked_source=None,static={self.identities[tuple(b['box'])]:tuple(b['box']) for b in static})
            for i,pos in enumerate(ps):
                h,w=sizes[i]
                for a,m in sorted(self.motions.items()):
                    dy,dx=m['delta'];q=(pos[0]+dy,pos[1]+dx)
                    if not(0<=q[0]<=64-h and 0<=q[1]<=64-w) or any(overlap((*q,h,w),b['box']) for b in static):continue
                    j=1-i;dest=list(ps)
                    if overlap((*q,h,w),(*ps[j],*sizes[j])):
                        if not self.push_memory:continue
                        pushed=(ps[j][0]+dy,ps[j][1]+dx);hh,ww=sizes[j]
                        if not(0<=pushed[0]<=64-hh and 0<=pushed[1]<=64-ww) or overlap((*pushed,hh,ww),(*ps[i],h,w)) or any(overlap((*pushed,hh,ww),b['box']) for b in static):continue
                        pattern=pat(pushed,sizes[j])
                        if any(v not in allowed for v in pattern):continue
                        blocked=False
                        for c in self.push_constraints:
                            if c['identity']!=ids[j] or tuple(c['delta'])!=(dy,dx):continue
                            yy,xx=c['destination'];bh,bw=c['object']['box'][2:];normalized=tuple(floor if inside((yy+k//bw,xx+k%bw),c['object']['box']) else v for k,v in enumerate(c['pattern']))
                            if normalized==pattern:blocked=True;break
                        if blocked:continue
                        dest[j]=pushed
                    else:
                        pattern=pat(q,sizes[i])
                        if any(v not in allowed for v in pattern) or any(c['identity']==ids[i] and tuple(c['delta'])==(dy,dx) and tuple(c['pattern'])==pattern for c in self.constraint_hypotheses):continue
                        dest[i]=q
                    key=(tuple(dest),i);gg=g+1+(i!=selected)
                    if gg>=cost.get(key,10**9):continue
                    cost[key]=gg;parent[key]=(state,i,a);serial+=1;heapq.heappush(queue,(gg+heuristic(key[0]),-gg,serial,key))
        return None
    def cached_pair(self):
        p=self.pair_plan
        if not p:return None
        lookup={self.identities[tuple(b['box'])]:b for b in self.objects}
        if not all(i in lookup for i in p['ids']):self.pair_plan=None;return None
        if any(i not in lookup or tuple(lookup[i]['box'])!=box for i,box in p['static'].items()):self.pair_plan=None;return None
        current=tuple(tuple(lookup[i]['box'][:2]) for i in p['ids']);old=self.previous
        if old and old['source']!=p['checked_source']:
            p['checked_source']=old['source']
            if old['action']!=6:
                actor,action=p['moves'][0]
                if old['action']==action and current==p['states'][0]:p['moves'].pop(0);p['states'].pop(0);p['before']=current
                else:self.pair_plan=None;return None
        if current!=p['before'] or not p['moves']:self.pair_plan=None;return None
        bodies=[lookup[i] for i in p['ids']];return bodies,[(p['ids'].index(i),a) for i,a in p['moves']]
    def joint_plan(self,raw):
        if len(self.objects)<=2:return super().joint_plan(raw)
        cached=self.cached_pair()
        if cached:return cached
        if not self.use_subgoals:
            result=super().joint_plan(raw)
            if result:return result
            self.use_subgoals=True
        if not self.push_memory or not self.motions:return None
        choices=[]
        for target in self.objects:
            if any(tuple(target['box'][:2])==(g['box'][0]+1,g['box'][1]+1) for g in self.goals):continue
            for goal in self.goals:
                if tuple(goal['box'][2:])!=(target['box'][2]+2,target['box'][3]+2):continue
                if any(tuple(b['box'][:2])==(goal['box'][0]+1,goal['box'][1]+1) for b in self.objects):continue
                distance=sum(abs(target['box'][i]-goal['box'][i]-1) for i in (0,1))
                for helper in self.objects:
                    if helper is target:continue
                    approach=sum(abs(target['box'][i]-helper['box'][i]) for i in (0,1));choices.append((distance,approach,tuple(target['box']),tuple(helper['box']),target,helper,goal))
        for _,_,_,_,target,helper,goal in sorted(choices,key=lambda c:c[:4])[:4]:
            plan=self.pair_search(raw,target,helper,goal)
            if not plan:continue
            plan['checked_source']=self.previous['source'] if self.previous else None;self.pair_plan=plan;self.pair_diagnostics.append(dict(source=self.t,target=plan['target'],helper=plan['ids'][1],goal=copy.deepcopy(goal),expanded=plan['expanded'],remaining_steps=len(plan['moves']),plan_is_hypothesis=True));return self.cached_pair()
        return None
    def answer(self,*args,**kwargs):
        r=super().answer(*args,**kwargs)
        if not r['done']:r['certificate']['pair_subgoals']=copy.deepcopy(self.pair_diagnostics)
        return r
