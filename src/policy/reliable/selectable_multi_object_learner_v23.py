"""Maintain a subgoal through replanning and match only observed terrain fringes."""
import copy,heapq
from collections import Counter,deque
from selectable_multi_object_learner_v22 import Agent as Base
from selectable_rect_push_core_v2 import overlap
from selectable_rect_core_v1 import inside,same
class Agent(Base):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.committed_subgoal=None
    def reset_level(self,raw):super().reset_level(raw);self.committed_subgoal=None
    def fringe_matches(self,rule,pattern,object_key='body'):
        y,x=rule['destination'];body=rule[object_key];h,w=body['box'][2:]
        indices=[k for k in range(h*w) if not inside((y+k//w,x+k%w),body['box'])]
        return bool(indices) and len(pattern)==len(rule['pattern']) and all(pattern[k]==rule['pattern'][k] for k in indices)
    def route(self,raw,body,goal):
        start=tuple(body['box'][:2]);target=(goal['box'][0]+1,goal['box'][1]+1);h,w=body['box'][2:];others=[q for q in self.objects if not same(q,body)];allowed={self.floor}|{g['ink'] for g in self.goals}|self.extra_terrain
        todo=deque([start]);parents={start:None}
        while todo:
            at=todo.popleft()
            if at==target:
                route=[]
                while parents[at] is not None:prev,a=parents[at];route.append(a);at=prev
                return route[::-1]
            for a,m in sorted(self.motions.items()):
                dy,dx=m['delta'];q=(at[0]+dy,at[1]+dx)
                if q in parents or not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
                if any(inside((y,x),o['box']) for y in range(q[0],q[0]+h) for x in range(q[1],q[1]+w) for o in others):continue
                if any(not inside((y,x),body['box']) and raw['frame'][y][x] not in allowed for y in range(q[0],q[0]+h) for x in range(q[1],q[1]+w)):continue
                context=self.context(raw,q,self.objects,body)
                if any(f['action']==a and tuple(f['body']['box'][:2])==at and f['context']==context for f in self.failures):continue
                ident=self.identities.get(tuple(body['box']))
                if any(c['identity']==ident and tuple(c['delta'])==tuple(m['delta']) and self.fringe_matches(c,context[0]) for c in self.constraint_hypotheses):continue
                parents[q]=(at,a);todo.append(q)
        return None
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
                            if self.fringe_matches(c,pattern,object_key='object'):blocked=True;break
                        if blocked:continue
                        dest[j]=pushed
                    else:
                        pattern=pat(q,sizes[i])
                        if any(v not in allowed for v in pattern) or any(c['identity']==ids[i] and tuple(c['delta'])==(dy,dx) and self.fringe_matches(c,pattern) for c in self.constraint_hypotheses):continue
                        dest[i]=q
                    key=(tuple(dest),i);gg=g+1+(i!=selected)
                    if gg>=cost.get(key,10**9):continue
                    cost[key]=gg;parent[key]=(state,i,a);serial+=1;heapq.heappush(queue,(gg+heuristic(key[0]),-gg,serial,key))
        return None
    def joint_plan(self,raw):
        if len(self.objects)<=2:return super().joint_plan(raw)
        if self.committed_subgoal:
            body=next((b for b in self.objects if self.identities[tuple(b['box'])]==self.committed_subgoal['target']),None)
            goal=self.committed_subgoal['goal']
            if body is None or tuple(body['box'][:2])==(goal['box'][0]+1,goal['box'][1]+1):self.committed_subgoal=None
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
                    approach=sum(abs(target['box'][i]-helper['box'][i]) for i in (0,1));priority=int(self.committed_subgoal is not None and self.identities[tuple(target['box'])]!=self.committed_subgoal['target']);choices.append((priority,distance,approach,tuple(target['box']),tuple(helper['box']),target,helper,goal))
        for _,_,_,_,_,target,helper,goal in sorted(choices,key=lambda c:c[:5])[:4]:
            plan=self.pair_search(raw,target,helper,goal)
            if not plan:continue
            plan['checked_source']=self.previous['source'] if self.previous else None;self.pair_plan=plan;self.committed_subgoal=dict(target=plan['target'],goal=copy.deepcopy(goal));self.pair_diagnostics.append(dict(source=self.t,target=plan['target'],helper=plan['ids'][1],goal=copy.deepcopy(goal),expanded=plan['expanded'],remaining_steps=len(plan['moves']),plan_is_hypothesis=True));return self.cached_pair()
        return None
