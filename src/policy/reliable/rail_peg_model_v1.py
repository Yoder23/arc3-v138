"""Visible carrier geometry and joint jump/rail search. All rules remain testable hypotheses."""
from collections import deque
import heapq
from matrix_motion_learner_v6 import objects
from peg_jump_inquiry_v2 import scene,pegs

def carrier(frame,size):
 hits=[]
 for o in objects(frame):
  if o.get('parts'):continue
  y,x,h,w=o['box']
  if h!=w or h!=size+2 or not(1<y<62-h and 1<x<62-w):continue
  expected={(dy,dx)for dy in range(h)for dx in range(w)if dy in (0,h-1)or dx in(0,w-1)}
  if set(o['shape'])==expected:hits.append(o)
 return hits[0] if len(hits)==1 else None

def layout(frame):
 s=scene(frame)
 if not s:return None
 o=carrier(frame,s['size'])
 if not o:return None
 y,x,h,w=o['box'];pos=(y+1,x+1);k=s['size']//2-1;track=frame[y-1][x-1];pitch=s['pitch'];rails=[]
 for yy in range(pos[0]%pitch,65-s['size'],pitch):
  for xx in range(pos[1]%pitch,65-s['size'],pitch):
   if (yy,xx)==pos or all(frame[yy+dy][xx+dx]==track for dy in (k,k+1)for dx in(k,k+1)):rails.append((yy,xx))
 return dict(scene=s,carrier=o,track=track,rails=rails,initial_position=pos)

def occupancy(frame,L,pos):
 s=L['scene'];k=(s['size']-1)//2
 return frozenset(p for p in list(map(tuple,s['cells']))+[pos] if frame[p[0]+k][p[1]+k]==s['mark'])

def rail_paths(L,at):
 pitch=L['scene']['pitch'];cells=set(map(tuple,L['rails']));parents={at:None};todo=deque([at])
 while todo:
  p=todo.popleft()
  for dy,dx in ((-pitch,0),(pitch,0),(0,-pitch),(0,pitch)):
   q=p[0]+dy,p[1]+dx
   if q in cells and q not in parents:parents[q]=(p,(dy,dx));todo.append(q)
 out={}
 for q in parents:
  steps=[];p=q
  while parents[p]:p,d=parents[p];steps.append(d)
  out[q]=steps[::-1]
 return out

def search(L,at,occupied,limit=60000):
 static=set(map(tuple,L['scene']['cells']));pitch=L['scene']['pitch'];allpaths={p:rail_paths(L,p)for p in map(tuple,L['rails'])};start=(at,occupied);serial=0;queue=[(0,0,at,occupied,[])];best={start:0};n=0
 while queue and n<limit:
  cost,_,pos,marks,plan=heapq.heappop(queue);n+=1
  if cost!=best[(pos,marks)]:continue
  if len(marks)==1:return plan,n
  for dest,steps in allpaths[pos].items():
   shifted=(marks-{pos})|{dest} if pos in marks else marks;cells=static|{dest}
   for a in sorted(shifted):
    for dy,dx in ((-pitch,0),(pitch,0),(0,-pitch),(0,pitch)):
     b=a[0]+dy,a[1]+dx;c=a[0]+2*dy,a[1]+2*dx
     if b not in shifted or c in shifted or c not in cells:continue
     after=frozenset((shifted-{a,b})|{c});key=dest,after;g=cost+len(steps)+2
     if g<best.get(key,10**9):
      best[key]=g;serial+=1;heapq.heappush(queue,(g,serial,dest,after,plan+[dict(travel_to=dest,steps=steps,jump=(a,b,c))]))
 return None,n
