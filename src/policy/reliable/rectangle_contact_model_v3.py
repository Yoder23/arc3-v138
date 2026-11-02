"""Candidate constant-perimeter contact deformations, to be tested against observations."""
import heapq

def points(box):
 a,b,c,d=box;return {(y,x) for y in range(a,c+1) for x in range(b,d+1) if y in (a,c) or x in (b,d)}

def valid(box,site):
 a,b,c,d=box
 return c-a>=3 and d-b>=3 and 0<=(a+c)/2<62 and 0<=(b+d)/2<64 and not points(box)&site

def advance(box,delta,site,model='turn_ccw'):
 a,b,c,d=box;dy,dx=delta;translated=(a+dy,b+dx,c+dy,d+dx)
 if valid(translated,site):return translated
 if dy:
  shrunk=[a+dy if dy>0 else a,b,c+dy if dy<0 else c,d];size=abs(dy)
  sides=[-1 if dy<0 else 1,1 if dy<0 else -1]
 else:
  shrunk=[a,b+dx if dx>0 else b,c,d+dx if dx<0 else d];size=abs(dx)
  sides=[-1 if dx>0 else 1,1 if dx>0 else -1]
 if model=='centered':
  q=shrunk[:]
  if dy:
   span=d-b;anchor=b+((span//size+1)//2)*size;new_span=span+size;q[1]=anchor-((new_span//size+1)//2)*size;q[3]=q[1]+new_span
  else:
   span=c-a;anchor=a+((span//size+1)//2)*size;new_span=span+size;q[0]=anchor-((new_span//size+1)//2)*size;q[2]=q[0]+new_span
  return tuple(q) if valid(q,site) else tuple(box)
 if model=='turn_cw':sides.reverse()
 if model.startswith('contact'):
  hit=points(translated)&site
  if hit:
   coordinate=sum((x if dy else y) for y,x in hit)/len(hit);center=(b+d)/2 if dy else (a+c)/2;prefer=-1 if coordinate<center else 1;sides=[prefer,-prefer]
 if model.endswith('_strict'):sides=sides[:1]
 for side in sides:
  q=shrunk[:]
  if dy:q[1 if side<0 else 3]+=side*size
  else:q[0 if side<0 else 2]+=side*size
  if valid(q,site):return tuple(q)
 return tuple(box)

def goal_boxes(initial,targets):
 a,b,c,d=initial;perimeter=(c-a)+(d-b);out=[]
 for h in range(3,perimeter,3):
  w=perimeter-h
  for y in range(a%3,62-h,3):
   for x in range(b%3,64-w,3):
    q=(y,x,y+h,x+w)
    if set(map(tuple,targets))<=points(q):out.append(q)
 return out

def plan(box,color,target,targets,site,pads,models,mechanism,blocked=(),limit=60000,forbidden_colors=()):
 start=tuple(box);goals=goal_boxes(start,targets)
 if not goals:return None,dict(reason='no_goal_box_with_retained_perimeter')
 def heuristic(q,c):
  h=min(max(abs(q[0]-g[0])+abs(q[1]-g[1]),abs(q[2]-g[2])+abs(q[3]-g[3]))/3 for g in goals)
  if c!=target:
   p=next(p for p in pads if p['color']==target);distance=min(max(p['y']-1-y,0,y-p['y']-p['size'])+max(p['x']-1-x,0,x-p['x']-p['size']) for y,x in points(q))/3;h=max(h,distance)
  return h
 queue=[(heuristic(start,color)*2,0,start,color,[])];cost={(start,color):0};expanded=0
 while queue and expanded<limit:
  _,g,q,c,path=heapq.heappop(queue)
  if cost[q,c]!=g:continue
  expanded+=1
  if c==target and q in goals:return path,dict(expanded=expanded,goal=list(q))
  for action,m in sorted(models.items()):
   if (q,c,action) in blocked:continue
   nxt=advance(q,m['delta'],site,mechanism)
   touched={p['color'] for p in pads if any(p['y']-1<=y<p['y']+p['size']+1 and p['x']-1<=x<p['x']+p['size']+1 for y,x in points(nxt))}
   if len(touched)>1:continue
   nc=next(iter(touched)) if touched else c
   if nc in forbidden_colors or cost.get((nxt,nc),10**9)<=g+1:continue
   cost[nxt,nc]=g+1;heapq.heappush(queue,(g+1+2*heuristic(nxt,nc),g+1,nxt,nc,path+[action]))
 return None,dict(expanded=expanded,frontier=len(queue))
