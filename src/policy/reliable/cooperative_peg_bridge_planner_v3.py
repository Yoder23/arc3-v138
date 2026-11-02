"""Retained movable stepping tokens as temporary bridges between visible regions.

A relaxed jump graph proposes a first jump; a real joint carrier-state search
must establish that jump before it can enter a plan. No proposed bridge is
an observation, and all predicted outcomes still require actual reconciliation.
"""
from collections import deque,Counter
import heapq
from cooperative_peg_joint_model_v4 import search as ordinary_search


def shifted_state(state,rails,delta):
 pos,marks,helpers,mounted=state;dy,dx=delta
 proposed={p:(p[0]+dy,p[1]+dx)if(p[0]+dy,p[1]+dx)in rails else p for p in pos}
 while True:
  counts=Counter(proposed.values());blocked={q for q,n in counts.items()if n>1}
  updates={p:p for p,q in proposed.items()if q in blocked and q!=p}
  if not updates:break
  proposed.update(updates)
 if all(p==q for p,q in proposed.items()):return None
 def moved(tokens):return frozenset((tokens-set(pos))|{proposed[p]for p in pos if p in tokens})
 return tuple(sorted(proposed.values())),moved(marks),moved(helpers),moved(mounted)


def step_record(state,delta,fixed):
 pos,marks,helpers,mounted=state
 return dict(kind='move',delta=delta,positions_after=pos,ordinary_after=sorted(marks),helpers_after=sorted(helpers),pivots_after=sorted(fixed|mounted))


def relaxed_first_steps(static,rails,marks,helpers,fixed,pitch,has_mobile,limit=4096,empty_reachable=None):
 # Hypothesize placement of a witnessed movable stepping token on a visible rail.
 allowed=static|rails;start=frozenset(marks);todo=deque([(start,None)]);seen={start};result=[]
 while todo and len(seen)<=limit:
  tokens,first=todo.popleft()
  for a in sorted(tokens):
   # A token aboard a carrier can traverse adjacent visible rail cells.
   # This is relaxed reachability; setup_jump must find a real joint control path.
   if a in rails:
    for dy,dx in[(-pitch,0),(pitch,0),(0,-pitch),(0,pitch)]:
     q=a[0]+dy,a[1]+dx;carried=frozenset((tokens-{a})|{q})
     if q in rails and q not in tokens|helpers|fixed and carried not in seen:
      seen.add(carried);todo.append((carried,first))
   for dy,dx in[(-pitch,0),(pitch,0),(0,-pitch),(0,pitch)]:
    b=a[0]+dy,a[1]+dx;z=a[0]+2*dy,a[1]+2*dx
    if z not in allowed or z in tokens|helpers|fixed:continue
    if first is None and empty_reachable is not None and z not in static|empty_reachable:continue
    if b in tokens:next_tokens=(tokens-{a,b})|{z}
    elif b in helpers|fixed or has_mobile and b in rails:next_tokens=(tokens-{a})|{z}
    else:continue
    jump=first or(a,b,z)
    if len(next_tokens)<len(start):
     if jump not in result:result.append(jump)
     if len(result)>=12:return result
    elif next_tokens not in seen:seen.add(next_tokens);todo.append((frozenset(next_tokens),jump))
 return result


def setup_jump(static,rails,state,fixed,pitch,jump,limit=12000):
 a,b,z=jump;directions=[(-pitch,0),(pitch,0),(0,-pitch),(0,pitch)]
 distances={}
 for target in (a,b,z):
  d={target:0};todo=deque([target])
  while todo:
   y,x=todo.popleft()
   for dy,dx in directions:
    q=y+dy,x+dx
    if q in rails and q not in d:d[q]=d[y,x]+1;todo.append(q)
  distances[target]=d
 def estimate(s):
  pos,marks,helpers,mounted=s;occupied=marks|helpers|fixed|mounted
  actor=min((distances[a].get(p,1000)for p in marks),default=1000)if a not in marks else 0
  bridge=0 if b in occupied else min((distances[b].get(p,1000)for p in mounted),default=1000)
  landing=0 if z in static or z in set(pos)-occupied else min((distances[z].get(p,1000)for p in set(pos)-occupied),default=1000)
  return max(actor,bridge,landing)
 best={state:0};parent={state:None};edge={};queue=[(4*estimate(state),0,0,state)];serial=expanded=0
 while queue and expanded<limit:
  _,cost,_,s=heapq.heappop(queue)
  if best[s]!=cost:continue
  expanded+=1;pos,marks,helpers,mounted=s;occupied=marks|helpers|fixed|mounted
  if a in marks and b in occupied and z not in occupied and z in static|set(pos):
   preserve=b in helpers|fixed|mounted;newmarks=(marks-{a})|{z}if preserve else(marks-{a,b})|{z}
   landing=dict(kind='jump',jump=jump,actor='ordinary',preserves_intermediate=preserve,ordinary_after=sorted(newmarks),helpers_after=sorted(helpers),pivots_after=sorted(fixed|mounted))
   path=[landing];end=(pos,frozenset(newmarks),helpers,mounted)
   while parent[s]is not None:path.append(edge[s]);s=parent[s]
   return list(reversed(path)),end,dict(expanded=expanded,seen=len(best),exhausted=False)
  for delta in directions:
   q=shifted_state(s,rails,delta)
   if q is None or cost+1>=best.get(q,10**9):continue
   h=estimate(q)
   if h>=1000:continue
   best[q]=cost+1;parent[q]=s;edge[q]=step_record(q,delta,fixed);serial+=1
   heapq.heappush(queue,(cost+1+4*h,cost+1,serial,q))
 return None,None,dict(expanded=expanded,seen=len(best),exhausted=not queue)


def search(cells,rails,positions,ordinary,helpers,pivots,pitch,limit=60000,target_count=1,goal_mode='reduce',frontiers=()):
 args=(cells,rails,positions,ordinary,helpers,pivots,pitch)
 # Preserve the established planner when no mobile stepping token is present.
 if not set(map(tuple,pivots))&set(map(tuple,positions))or goal_mode!='reduce':
  return ordinary_search(*args,limit=limit,target_count=target_count,goal_mode=goal_mode,frontiers=frontiers)
 static=set(map(tuple,cells));rails=set(map(tuple,rails));fixed=frozenset(map(tuple,pivots))-set(map(tuple,positions))
 state=(tuple(sorted(map(tuple,positions))),frozenset(map(tuple,ordinary)),frozenset(map(tuple,helpers)),frozenset(map(tuple,pivots))&set(map(tuple,positions)))
 path=[];proof=[];visited=set()
 for stage in range(8):
  if len(state[1])<=target_count:return path,dict(expanded=sum(x['search']['expanded']for x in proof),seen=len(visited),exhausted=False,target_count=target_count,goal_mode=goal_mode,bridge_stages=proof)
  if state in visited:break
  visited.add(state)
  empty=set(state[0])-state[1]-state[2]-state[3];reachable=set(empty);todo=deque(empty)
  while todo:
   y,x=todo.popleft()
   for dy,dx in[(-pitch,0),(pitch,0),(0,-pitch),(0,pitch)]:
    q=y+dy,x+dx
    if q in rails and q not in reachable:reachable.add(q);todo.append(q)
  proposals=relaxed_first_steps(static,rails,state[1],state[2],fixed,pitch,bool(state[3]),empty_reachable=reachable);choices=[]
  for rank,jump in enumerate(proposals):
   candidate,end,stats=setup_jump(static,rails,state,fixed,pitch,jump,limit=min(limit,12000))
   if candidate and end not in visited:choices.append((rank,jump,candidate,end,stats))
  if not choices:break
  _,jump,chosen,state,stats=min(choices,key=lambda q:(q[0],q[1]));path+=chosen;proof.append(dict(jump=jump,search=stats,steps=len(chosen)))
 return ordinary_search(*args,limit=limit,target_count=target_count,goal_mode=goal_mode,frontiers=frontiers)
