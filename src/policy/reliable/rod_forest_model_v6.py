"""A testable subtree-rotation and axial-extension model inferred from legal rod geometry."""
import heapq,itertools
from collections import deque
from rod_forest_scene_v2 import key

def joint(v):
 y,x,h,w,dx,dy=v
 return (y+1 if dx else (y if dy<0 else y+h-1),x+1 if dy else (x if dx<0 else x+w-1))
def topology(sc):
 s=sc['state'];n=len(sc['bodies']);points=[joint(s[6*i:6*i+6]) for i in range(n)];edges=[]
 for i in range(n):
  v=s[6*i:6*i+6];y,x=points[i];dx,dy=v[4:];length=v[3] if dx else v[2];tip=(y-dy*(length+1),x-dx*(length+1))
  edges.extend([i,j] for j,p in enumerate(points) if i!=j and p==tip)
 if len({b for a,b in edges})!=len(edges):return None
 descendants=[]
 for i in range(n):
  group={i}
  for _ in range(n):group|={b for a,b in edges if a in group}
  if any(a in group and b==i for a,b in edges):return None
  descendants.append(sorted(group))
 return dict(edges=edges,descendants=descendants,endpoints=[next(i for i,b in enumerate(sc['bodies']) if b['color']==e['color']) for e in sc['ends']])
def constraints(sc):
 prefix=[[0]*65 for _ in range(65)]
 for y,x in sc['walls']:prefix[y+1][x+1]=1
 for y in range(1,65):
  for x in range(1,65):prefix[y][x]+=prefix[y-1][x]+prefix[y][x-1]-prefix[y-1][x-1]
 return dict(walls=prefix,height=min(p['y'] for p in sc['controls']),bodies=len(sc['bodies']),allow_top=[i for i,b in enumerate(sc['bodies']) if b['color'] in sc.get('allow_offscreen_top_colors',[])])
def valid(s,limits):
 boxes=[];pref=limits['walls']
 for i in range(limits['bodies']):
  y,x,h,w,dx,dy=s[6*i:6*i+6]
  if min(h,w)<2 or h!=3 and w!=3:return False
  top=y-(dy<0);left=x-(dx<0);bottom=y+h+(dy>0);right=x+w+(dx>0)
  if (top<0 and i not in limits['allow_top']) or left<0 or bottom>limits['height'] or right>64:return False
  visible_top=max(0,top)
  if pref[bottom][right]-pref[visible_top][right]-pref[bottom][left]+pref[visible_top][left]:return False
  if any(max(top,a)<min(bottom,c) and max(left,b)<min(right,d) for a,b,c,d in boxes):return False
  boxes.append((top,left,bottom,right))
 return True

def rotate_raw(s,index,quarter,tree):
 out=list(s);cy,cx=joint(s[6*index:6*index+6]);group=tree['descendants'][index];n=len(tree['descendants'])
 def point(y,x):
  for _ in range(quarter%4):y,x=cy-(x-cx),cx+(y-cy)
  return y,x
 for i in group:
  y,x,h,w,dx,dy=s[6*i:6*i+6];ps=[point(yy,xx) for yy in (y,y+h-1) for xx in (x,x+w-1)]
  for _ in range(quarter%4):dx,dy=dy,-dx
  out[6*i:6*i+6]=[min(p[0] for p in ps),min(p[1] for p in ps),max(p[0] for p in ps)-min(p[0] for p in ps)+1,max(p[1] for p in ps)-min(p[1] for p in ps)+1,dx,dy]
 for j,i in enumerate(tree['endpoints']):
  if i in group:out[6*n+2*j:6*n+2*j+2]=point(*s[6*n+2*j:6*n+2*j+2])
 return tuple(out)
def internally_clear(s,index,tree):
 group={index}
 for _ in tree['descendants']:
  group|={a for a,b in tree['edges'] if b in group};group|={b for a,b in tree['edges'] if a in group}
 boxes=[]
 for i in group:
  y,x,h,w,dx,dy=s[6*i:6*i+6];box=(y-(dy<0),x-(dx<0),y+h+(dy>0),x+w+(dx>0))
  if any(max(box[0],q[0])<min(box[2],q[2]) and max(box[1],q[1])<min(box[3],q[3]) for q in boxes):return False
  boxes.append(box)
 return True

def predict(s,index,mode,amount,tree,limits,rotates_descendants=True):
 if mode=='rotate_joint':
  for turn in (1,2,3):
   candidate=rotate_raw(s,index,amount*turn,tree)
   if internally_clear(candidate,index,tree):return candidate if valid(candidate,limits) else None
  return None
 n=len(tree['descendants']);out=list(s);v=s[6*index:6*index+6];cy,cx=joint(v);group=tree['descendants'][index]
 if mode=='rotate':
  group=group if rotates_descendants else [index]
  def rot(y,x):return (cy-amount*(x-cx),cx+amount*(y-cy))
  for i in group:
   y,x,h,w,dx,dy=s[6*i:6*i+6];points=[rot(yy,xx) for yy in (y,y+h-1) for xx in (x,x+w-1)];ys=[p[0] for p in points];xs=[p[1] for p in points];out[6*i:6*i+6]=[min(ys),min(xs),w,h,amount*dy,-amount*dx]
  for j,index0 in enumerate(tree['endpoints']):
   if index0 in group:out[6*n+2*j:6*n+2*j+2]=rot(*s[6*n+2*j:6*n+2*j+2])
 else:
  y,x,h,w,dx,dy=v;length=(w if dx else h)+amount
  if length<2:return None
  out[6*index:6*index+4]=[cy-1,cx if dx<0 else cx-length+1,3,length] if dx else [cy if dy<0 else cy-length+1,cx-1,length,3]
  for i in group:
   if i!=index:out[6*i]-=dy*amount;out[6*i+1]-=dx*amount
  for j,index0 in enumerate(tree['endpoints']):
   if index0 in group:out[6*n+2*j]-=dy*amount;out[6*n+2*j+1]-=dx*amount
 result=tuple(out)
 return result if valid(result,limits) else None

def fit(old,new,p,tree):
 i=next(i for i,b in enumerate(old['bodies']) if b['color']==p['color']);a=old['state'];b=new['state'];limits=constraints(old)
 if a==b:return None
 if any(key(q)==key(p) for q in old['turns']):
  candidates=[dict(index=i,mode=mode,amount=d,descendants=sub) for mode in ('rotate','rotate_joint') for sub in (False,True) for d in (-1,1)]
 else:
  u=a[6*i:6*i+6];v=b[6*i:6*i+6];d=(v[3] if v[4] else v[2])-(u[3] if u[4] else u[2]);candidates=[dict(index=i,mode='extend',amount=d,descendants=True)] if d else []
 hits=[c for c in candidates if predict(a,c['index'],c['mode'],c['amount'],tree,limits,c['descendants'])==tuple(b)]
 if not hits:return None
 return hits[-1]

def plan(sc,tree,models,blocked=()):
 limits=constraints(sc);goals=[tuple(v for p in order for v in p) for order in itertools.permutations(sc['goals'])];offset=6*len(sc['bodies']);start=tuple(sc['state']);queue=[(0,0,start,[])];cost={start:0};expanded=0
 blocked_cells={(yy,xx) for y,x in sc['walls'] for yy in range(max(0,y-1),min(limits['height'],y+2)) for xx in range(max(0,x-1),min(64,x+2))};maps={}
 for goal in sc['goals']:
  g=tuple(goal);d={g:0};q=deque([g])
  while q:
   y,x=q.popleft()
   for yy,xx in [(y-1,x),(y+1,x),(y,x-1),(y,x+1)]:
    if 0<=yy<limits['height'] and 0<=xx<64 and (yy,xx) not in blocked_cells and (yy,xx) not in d:d[yy,xx]=d[y,x]+1;q.append((yy,xx))
  maps[g]=d
 def h(s):return min(sum(maps[tuple(goal[i:i+2])].get(tuple(s[offset+i:offset+i+2]),10000) for i in range(0,len(goal),2))/3 for goal in goals)
 best=(h(start),start)
 while queue and expanded<300000:
  _,g,s,path=heapq.heappop(queue)
  if g!=cost[s]:continue
  expanded+=1
  if s[offset:] in goals:
   LAST_SEARCH.update(expanded=expanded,frontier=len(queue),best=0);return path
  for k,m in sorted(models.items()):
   if len(m['support'])<2 or (s,k) in blocked:continue
   q=m['model'];nxt=predict(s,q['index'],q['mode'],q['amount'],tree,limits,q['descendants'])
   if nxt is None or cost.get(nxt,10**9)<=g+1:continue
   cost[nxt]=g+1;hh=h(nxt)
   if hh<best[0]:best=(hh,nxt)
   heapq.heappush(queue,(g+1+2*hh,g+1,nxt,path+[k]))
 LAST_SEARCH.update(expanded=expanded,frontier=len(queue),best=best[0],closest=list(best[1]),states=len(cost))
 return None

LAST_SEARCH={}
