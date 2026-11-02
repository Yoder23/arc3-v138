"""Plan typed jumps jointly with independently constrained carrier motions."""
import heapq

def search(cells,rails,positions,ordinary,helpers,pivots,pitch,limit=60000,target_count=1,goal_mode='reduce',frontiers=()):
 static=set(map(tuple,cells));rails=set(map(tuple,rails));fixed=frozenset(map(tuple,pivots))-set(map(tuple,positions));initial=(tuple(sorted(map(tuple,positions))),frozenset(map(tuple,ordinary)),frozenset(map(tuple,helpers)),frozenset(map(tuple,pivots))&set(map(tuple,positions)));best={initial:0};parent={initial:None};edge={};queue=[(2*max(0,len(initial[1])-target_count),0,0,initial)];serial=0;expanded=0
 while queue and expanded<limit:
  _,cost,_,state=heapq.heappop(queue);pos,marks,assist,mounted=state
  if best[state]!=cost:continue
  expanded+=1
  complete=len(marks)<=target_count if goal_mode=='reduce'else bool(marks|assist)and (marks|assist)<=set(pos)if goal_mode=='load'else bool(marks&set(map(tuple,frontiers)))
  if complete:
   path=[]
   while parent[state]is not None:path.append(edge[state]);state=parent[state]
   return list(reversed(path)),dict(expanded=expanded,seen=len(best),exhausted=False,target_count=target_count,goal_mode=goal_mode)
  occupied=marks|assist|fixed|mounted;choices=[]
  for a in sorted(marks|assist):
   for dy,dx in[(-pitch,0),(pitch,0),(0,-pitch),(0,pitch)]:
    b=(a[0]+dy,a[1]+dx);z=(a[0]+2*dy,a[1]+2*dx)
    if b not in occupied or z in occupied or z not in static|set(pos):continue
    preserve=a in assist or b in assist|fixed|mounted;m=(marks-{a,b})|{z}if not preserve else(marks-{a})|{z}if a in marks else marks;h=(assist-{a})|{z}if a in assist else assist
    choices.append(((pos,frozenset(m),frozenset(h),mounted),2,dict(kind='jump',jump=(a,b,z),actor='helper'if a in assist else'ordinary',preserves_intermediate=preserve,ordinary_after=sorted(m),helpers_after=sorted(h),pivots_after=sorted(fixed|mounted))))
  for dy,dx in[(-pitch,0),(pitch,0),(0,-pitch),(0,pitch)]:
   shifted=tuple((y+dy,x+dx)if(y+dy,x+dx)in rails else(y,x)for y,x in pos)
   if shifted==pos or len(set(shifted))!=len(pos):continue
   def moved(tokens):return frozenset((tokens-set(pos))|{shifted[i]for i,p in enumerate(pos)if p in tokens})
   m=moved(marks);h=moved(assist);mobile=moved(mounted);dest=tuple(sorted(shifted));choices.append(((dest,m,h,mobile),1,dict(kind='move',delta=(dy,dx),positions_after=dest,ordinary_after=sorted(m),helpers_after=sorted(h),pivots_after=sorted(fixed|mobile))))
  for dest,weight,move in choices:
   g=cost+weight
   if g>=best.get(dest,10**9):continue
   best[dest]=g;parent[dest]=state;edge[dest]=move;serial+=1;heapq.heappush(queue,(g+2*max(0,len(dest[1])-target_count),g,serial,dest))
 return None,dict(expanded=expanded,seen=len(best),exhausted=not queue,target_count=target_count,goal_mode=goal_mode)
