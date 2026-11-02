"""A testable subtree-rotation and axial-extension model inferred from legal rod geometry."""
import heapq
from orientable_endpoint_scene_v4 import key

def joint(v):
 y,x,h,w,dx,dy=v
 return (y+1 if dx else (y if dy<0 else y+h-1),x+1 if dy else (x if dx<0 else x+w-1))
def topology(sc):
 s=sc['state'];n=len(sc['bodies']);points=[joint(s[6*i:6*i+6]) for i in range(n)];edges=[]
 for i in range(n):
  v=s[6*i:6*i+6];y,x=points[i];dx,dy=v[4:];length=v[3] if dx else v[2];tip=(y-dy*(length+1),x-dx*(length+1))
  edges.extend([i,j] for j,p in enumerate(points) if i!=j and p==tip)
 if len(edges)!=n-1 or len({b for a,b in edges})!=n-1:return None
 descendants=[]
 for i in range(n):
  group={i}
  for _ in range(n):group|={b for a,b in edges if a in group}
  if any(a in group and b==i for a,b in edges):return None
  descendants.append(sorted(group))
 return dict(edges=edges,descendants=descendants,endpoint=next(i for i,b in enumerate(sc['bodies']) if b['color']==sc['endpoint']['color']))
def constraints(sc):
 prefix=[[0]*65 for _ in range(65)]
 for y,x in sc['walls']:prefix[y+1][x+1]=1
 for y in range(1,65):
  for x in range(1,65):prefix[y][x]+=prefix[y-1][x]+prefix[y][x-1]-prefix[y-1][x-1]
 return dict(walls=prefix,height=min(p['y'] for p in sc['controls']))
def valid(s,limits):
 boxes=[];pref=limits['walls']
 for i in range((len(s)-2)//6):
  y,x,h,w,dx,dy=s[6*i:6*i+6]
  if min(h,w)<2 or h!=3 and w!=3:return False
  top=y-(dy<0);left=x-(dx<0);bottom=y+h+(dy>0);right=x+w+(dx>0)
  if top<0 or left<0 or bottom>limits['height'] or right>64:return False
  if pref[bottom][right]-pref[top][right]-pref[bottom][left]+pref[top][left]:return False
  if any(max(top,a)<min(bottom,c) and max(left,b)<min(right,d) for a,b,c,d in boxes):return False
  boxes.append((top,left,bottom,right))
 return True

def predict(s,index,mode,amount,tree,limits,rotates_descendants=True):
 n=(len(s)-2)//6;out=list(s);v=s[6*index:6*index+6];cy,cx=joint(v);group=tree['descendants'][index]
 if mode=='rotate':
  group=group if rotates_descendants else [index]
  def rot(y,x):return (cy-amount*(x-cx),cx+amount*(y-cy))
  for i in group:
   y,x,h,w,dx,dy=s[6*i:6*i+6];points=[rot(yy,xx) for yy in (y,y+h-1) for xx in (x,x+w-1)];ys=[p[0] for p in points];xs=[p[1] for p in points];out[6*i:6*i+6]=[min(ys),min(xs),w,h,amount*dy,-amount*dx]
  if tree['endpoint'] in group:out[-2:]=rot(*s[-2:])
 else:
  y,x,h,w,dx,dy=v;length=(w if dx else h)+amount
  if length<2:return None
  out[6*index:6*index+4]=[cy-1,cx if dx<0 else cx-length+1,3,length] if dx else [cy if dy<0 else cy-length+1,cx-1,length,3]
  for i in group:
   if i!=index:out[6*i]-=dy*amount;out[6*i+1]-=dx*amount
  if tree['endpoint'] in group:out[-2]-=dy*amount;out[-1]-=dx*amount
 result=tuple(out)
 return result if valid(result,limits) else None

def fit(old,new,p,tree):
 i=next(i for i,b in enumerate(old['bodies']) if b['color']==p['color']);a=old['state'];b=new['state'];limits=constraints(old)
 if a==b:return None
 if any(key(q)==key(p) for q in old['turns']):
  candidates=[dict(index=i,mode='rotate',amount=d,descendants=sub) for sub in (False,True) for d in (-1,1)]
 else:
  u=a[6*i:6*i+6];v=b[6*i:6*i+6];d=(v[3] if v[4] else v[2])-(u[3] if u[4] else u[2]);candidates=[dict(index=i,mode='extend',amount=d,descendants=True)] if d else []
 hits=[c for c in candidates if predict(a,c['index'],c['mode'],c['amount'],tree,limits,c['descendants'])==tuple(b)]
 if not hits:return None
 return hits[-1]

def plan(sc,tree,models,blocked=()):
 limits=constraints(sc);goal=sc['goals'][0];start=tuple(sc['state']);queue=[(0,0,start,[])];cost={start:0};expanded=0
 def h(s):return (abs(s[-2]-goal[0])+abs(s[-1]-goal[1]))/3
 while queue and expanded<120000:
  _,g,s,path=heapq.heappop(queue)
  if g!=cost[s]:continue
  expanded+=1
  if s[-2:]==tuple(goal):return path
  for k,m in sorted(models.items()):
   if len(m['support'])<2 or (s,k) in blocked:continue
   q=m['model'];nxt=predict(s,q['index'],q['mode'],q['amount'],tree,limits,q['descendants'])
   if nxt is None or cost.get(nxt,10**9)<=g+1:continue
   cost[nxt]=g+1;heapq.heappush(queue,(g+1+2*h(nxt),g+1,nxt,path+[k]))
 return None
