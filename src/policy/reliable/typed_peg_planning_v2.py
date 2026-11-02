from collections import Counter,deque
import heapq
from matrix_motion_learner_v6 import objects
from peg_jump_inquiry_v2 import scene

def carriers(frame,size,ink=None,known=()):
 out=[]
 for o in objects(frame):
  if o.get('parts') or (ink is not None and o['ink']!=ink):continue
  y,x,h,w=o['box'];expected={(dy,dx)for dy in range(h)for dx in range(w)if dy in(0,h-1)or dx in(0,w-1)}
  if h==w==size+2 and set(o['shape'])==expected:out.append(o)
 if ink is None and out:
  chosen=Counter(o['ink']for o in out).most_common(1)[0][0];out=[o for o in out if o['ink']==chosen]
 if ink is not None:
  for yy,xx in known:
   y,x=yy-1,xx-1;h=size+2;corners=[(0,0),(0,h-1),(h-1,0),(h-1,h-1)]
   if not any(o['box'][:2]==(y,x)for o in out) and all(frame[y+dy][x+dx]==ink for dy,dx in corners):out.append(dict(ink=ink,box=(y,x,h,h),shape=corners,occlusion_hypothesis='selection_overlay'))
 return sorted(out,key=lambda o:o['box'])
def layout(frame):
 s=scene(frame)
 if not s:return None
 bodies=carriers(frame,s['size'])
 if not bodies:return None
 pos=tuple((o['box'][0]+1,o['box'][1]+1)for o in bodies);y,x=bodies[0]['box'][:2];track=frame[y-1][x-1];pitch=s['pitch'];k=s['size']//2-1;rails=[]
 for yy in range(pos[0][0]%pitch,65-s['size'],pitch):
  for xx in range(pos[0][1]%pitch,65-s['size'],pitch):
   if (yy,xx)in pos or all(frame[yy+dy][xx+dx]==track for dy in(k,k+1)for dx in(k,k+1)):rails.append((yy,xx))
 return dict(scene=s,carriers=bodies,carrier_ink=bodies[0]['ink'],rails=rails,track=track,initial_positions=pos)
def shift(poses,marks,delta,rails):
 dy,dx=delta;new=tuple((y+dy,x+dx)if(y+dy,x+dx)in rails else(y,x)for y,x in poses)
 if len(set(new))!=len(new):return poses,marks
 moved={new[i]for i,p in enumerate(poses)if p in marks};return tuple(sorted(new)),frozenset((marks-set(poses))|moved)
def configs(L,start,limit=12000):
 rails=set(map(tuple,L['rails']));pitch=L['scene']['pitch'];todo=deque([start]);out={start:[]}
 while todo and len(out)<limit:
  p=todo.popleft()
  for d in((-pitch,0),(pitch,0),(0,-pitch),(0,pitch)):
   q,_=shift(p,frozenset(),d,rails)
   if q not in out:out[q]=out[p]+[d];todo.append(q)
 return out

def search(L,start,marks,limit=90000,goal_region=None,target_count=1):
 pivots=set(map(tuple,L.get('pivots',[])));static=set(map(tuple,L['scene']['cells']));rails=set(map(tuple,L['rails']));pitch=L['scene']['pitch'];cache={};pivots=frozenset(pivots);initial=(start,marks,pivots);best={initial:0};queue=[(2*(len(marks)-1),0,0,start,marks,pivots,[])];serial=0;n=0
 while queue and n<limit:
  _,cost,_,pos,occupied,pivots,plan=heapq.heappop(queue);n+=1
  if cost!=best[(pos,occupied,pivots)]:continue
  if (len(occupied)==1 if goal_region is None else sum(p in goal_region for p in occupied)==target_count):return plan,n
  if pos not in cache:cache[pos]=configs(L,pos)
  for dest,steps in cache[pos].items():
   q=pos;shifted=occupied;moving=pivots
   for d in steps:
    _,moving=shift(q,moving,d,rails);q,shifted=shift(q,shifted,d,rails)
   cells=static|set(dest)
   for a in sorted(shifted):
    for dy,dx in((-pitch,0),(pitch,0),(0,-pitch),(0,pitch)):
     b=a[0]+dy,a[1]+dx;c=a[0]+2*dy,a[1]+2*dx
     if b not in shifted|moving or c in shifted|moving or c not in cells or goal_region is not None and a not in goal_region:continue
     after=frozenset((shifted-{a,b})|{c});key=dest,after,moving;g=cost+len(steps)+2
     if g<best.get(key,10**9):best[key]=g;serial+=1;heapq.heappush(queue,(g+2*(len(after)-1),g,serial,dest,after,moving,plan+[dict(steps=steps,positions=dest,jump=(a,b,c))]))
 return None,n

def regions(L):
 cells=set(map(tuple,L['scene']['cells']))|set(map(tuple,L['rails']));pitch=L['scene']['pitch'];out=[]
 while cells:
  start=min(cells);cells.remove(start);part={start};todo=[start]
  while todo:
   y,x=todo.pop()
   for q in((y-pitch,x),(y+pitch,x),(y,x-pitch),(y,x+pitch)):
    if q in cells:cells.remove(q);part.add(q);todo.append(q)
  out.append(part)
 return out
