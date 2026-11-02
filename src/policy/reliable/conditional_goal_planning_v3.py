"""Compose a key-gated intermediate goal, reusable controls and finite refills."""
import heapq,itertools
from functools import lru_cache
from collections import deque
from math import lcm
from conditional_goal_motion_v1 import relaxed,resolve,covers as goal_cover
from key_control_clock_v1 import at
from key_resource_planning_v19 import search as prior

def search(scene,mask,controls,rules,shapes,colors,resources,consumed,meter,remaining,cost,motion=None,clocks=None,t=0,limit=150000,goal_contact=True,stationary_rejected=False):
 if not scene.get('joint_goal_target'):return prior(scene,mask,controls,rules,shapes,colors,resources,consumed,meter,remaining,cost,motion,clocks,t,limit=100000,goal_contact=goal_contact,stationary_rejected=stationary_rejected)
 from key_glyph_learning_v20 import covers,transform,DIRS
 motion=motion or {};clocks=clocks or {};gates=scene.get('conditional_goal_regions',[]);n=scene['actor'][2];goal=scene['goal'];target=(goal[0]+(goal[2]-n)//2,goal[1]+(goal[3]-n)//2);period=lcm(*[m['period']for m in clocks.values()])if clocks else 1;capacity=meter['capacity']//cost
 energy=remaining//cost;used=sum(1<<i for i,c in enumerate(controls)if c['box']in consumed);start=(scene['actor'][:2],scene['key'],scene['key_color'],energy,used,t%period,0);serial=itertools.count();parent={};best={(start[0],start[1],start[2],used,start[5],0):energy}
 optimistic=relaxed(motion,gates);positions={start[0]};todo=deque([start[0]]);back={}
 while todo:
  p=todo.popleft()
  for a,(dy,dx)in DIRS.items():
   q=optimistic.get((p,a,n),(p[0]+dy*n,p[1]+dx*n))
   if not all((y,x)in mask for y in range(q[0],q[0]+n)for x in range(q[1],q[1]+n)):continue
   back.setdefault(q,[]).append(p)
   if q not in positions:positions.add(q);todo.append(q)
 def distances(dest):
  d={dest:0};todo=deque([dest])
  while todo:
   q=todo.popleft()
   for p in back.get(q,[]):
    if p not in d:d[p]=d[q]+1;todo.append(p)
  return d
 targets=[target]+[(g['box'][0]+(g['box'][2]-n)//2,g['box'][1]+(g['box'][3]-n)//2)for g in gates];distances_to=[distances(p)for p in targets]
 def heuristic(s):
  p,key,color,en,u,phase,opened=s;closed=[i for i in range(len(gates))if not(opened>>i)&1]
  if closed:
   i=min(closed,key=lambda i:distances_to[i+1].get(p,100));g=gates[i];return distances_to[i+1].get(p,100)+distances_to[0].get(targets[i+1],100)+4*(key!=g['glyph'])+3*(color!=g['color'])
  return distances_to[0].get(p,100)+4*(key!=scene['target'])+3*(color!=scene['target_color'])
 @lru_cache(None)
 def opened_motion(opened):return relaxed(motion,[v for i,v in enumerate(gates)if(opened>>i)&1])
 @lru_cache(None)
 def transition(p,a,key,color,opened):
  q=resolve(opened_motion(opened),p,a,n,key,color,[v for i,v in enumerate(gates)if not(opened>>i)&1])
  if not valid(q):return p if clocks else None
  return q
 @lru_cache(None)
 def valid(q):return all((y,x)in mask for y in range(q[0],q[0]+n)for x in range(q[1],q[1]+n))
 @lru_cache(None)
 def entered(p,q,phase):return tuple((i,c['signature'])for i,c in enumerate(controls)if covers(q,n,at(c,clocks,phase+1))and not covers(p,n,at(c,clocks,phase)))
 @lru_cache(None)
 def gates_at(q):return tuple(i for i,v in enumerate(gates)if goal_cover(q,n,v))
 queue=[(2*heuristic(start),0,next(serial),start)];expanded=0
 while queue and expanded<limit:
  _,g,_,state=heapq.heappop(queue);expanded+=1;p,key,color,en,u,phase,opened=state
  if (p==target or not goal_contact)and key==scene['target']and color==scene['target_color']:
   path=[]
   while state!=start:state,a=parent[state];path.append(a)
   return path[::-1]
  if en<=0:continue
  for a,(dy,dx)in DIRS.items():
   q=transition(p,a,key,color,opened)
   if q is None:continue
   if stationary_rejected and q==p:continue
   nk,nc,ne,nu,no=key,color,en-1,u,opened
   for i in gates_at(q):
    v=gates[i]
    if nk==v['glyph']and nc==v['color']:no|=1<<i
   for i,sig in entered(p,q,phase):
    if sig in resources and not u&(1<<i):ne=capacity;nu|=1<<i
    nc=colors.get(sig,{}).get(nc,nc);ops=rules.get(sig);nk=shapes.get(sig,{}).get(nk,transform(nk,min(ops)if ops else 0))
   new=(q,nk,nc,ne,nu,(phase+1)%period,no);context=(q,nk,nc,nu,new[5],no)
   if ne>best.get(context,-1):best[context]=ne;parent[new]=(state,a);heapq.heappush(queue,(g+1+2*heuristic(new),g+1,next(serial),new))
 return None
