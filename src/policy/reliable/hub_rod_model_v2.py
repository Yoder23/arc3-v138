"""Shared-color extension and rigid hub rotation hypotheses with explicit extent policy."""
import heapq
from rod_forest_model_v6 import joint
from hub_rod_scene_v2 import key

def topology(sc):
 n=len(sc['bodies']);s=sc['state'];edges=[]
 for i,b in enumerate(sc['bodies']):
  if b['hub']:continue
  v=s[6*i:6*i+6];y,x=joint(v);dx,dy=v[4:];length=v[3] if dx else v[2];tip=(y-dy*(length+1),x-dx*(length+1))
  edges.extend([i,j] for j,c in enumerate(sc['bodies']) if j!=i and not c['hub'] and joint(s[6*j:6*j+6])==tip)
 descendants=[]
 for i in range(n):
  g={i}
  for _ in range(n):g|={b for a,b in edges if a in g}
  descendants.append(sorted(g))
 return dict(edges=edges,descendants=descendants,panels=[next(i for i,b in enumerate(sc['bodies']) if b['id']==p['body']) for p in sc['panels']],endpoint=next(i for i,b in enumerate(sc['bodies']) if b['id']==sc['ends'][0]['body']))

def limits(sc,allow_clip=False):
 prefix=[[0]*65 for _ in range(65)]
 for y,x in sc['walls']:prefix[y+1][x+1]=1
 for y in range(1,65):
  for x in range(1,65):prefix[y][x]+=prefix[y-1][x]+prefix[y][x-1]-prefix[y-1][x-1]
 return dict(prefix=prefix,clip=allow_clip)

def valid(s,sc,L):
 n=len(sc['bodies']);rects=[];pf=L['prefix']
 for i,b in enumerate(sc['bodies']):
  y,x,h,w,dx,dy=s[6*i:6*i+6]
  if min(h,w)<2 or h!=3 and w!=3:return False
  rects.append((y-(dy<0),x-(dx<0),y+h+(dy>0),x+w+(dx>0)))
 for j,p in enumerate(sc['panels']):
  y,x,h,w=s[6*n+4*j:6*n+4*j+4];rects.append((y,x,y+h,x+w))
 hub=sc['hub'];rects.append((hub['y'],hub['x'],hub['y']+hub['h'],hub['x']+hub['w']))
 seen=[]
 for i,r in enumerate(rects):
  a,b,c,d=r
  if min(a,b)<0 or c>63 or d>64:
   if not L['clip'] or i>=n or not sc['bodies'][i]['hub']:return False
  aa,bb,cc,dd=max(0,a),max(0,b),min(63,c),min(64,d)
  if aa<cc and bb<dd and pf[cc][dd]-pf[aa][dd]-pf[cc][bb]+pf[aa][bb]:return False
  if any(max(a,y)<min(c,z) and max(b,x)<min(d,w) for y,x,z,w in seen):return False
  seen.append(r)
 return True

def predict(s,sc,tree,color,mode,amount,L,check=True):
 n=len(sc['bodies']);out=list(s);cy,cx=sc['hub']['y']+1,sc['hub']['x']+1
 if mode=='rotate':
  def rot(y,x):return cy-amount*(x-cx),cx+amount*(y-cy)
  for i,b in enumerate(sc['bodies']):
   if not b['hub']:continue
   y,x,h,w,dx,dy=s[6*i:6*i+6];ps=[rot(yy,xx) for yy in (y,y+h-1) for xx in (x,x+w-1)];out[6*i:6*i+6]=[min(y for y,x in ps),min(x for y,x in ps),w,h,amount*dy,-amount*dx]
 else:
  for i,b in enumerate(sc['bodies']):
   if b['color']!=color:continue
   y,x,h,w,dx,dy=s[6*i:6*i+6];cy0,cx0=joint(s[6*i:6*i+6]);length=(w if dx else h)+amount
   if length<2 or length>62:return None
   out[6*i:6*i+4]=[cy0-1,cx0 if dx<0 else cx0-length+1,3,length] if dx else [cy0 if dy<0 else cy0-length+1,cx0-1,length,3]
   for j in tree['descendants'][i]:
    if j!=i:out[6*j]-=dy*amount;out[6*j+1]-=dx*amount
   for j,parent in enumerate(tree['panels']):
    if parent in tree['descendants'][i]:out[6*n+4*j]-=dy*amount;out[6*n+4*j+1]-=dx*amount
   if tree['endpoint'] in tree['descendants'][i]:out[-2]-=dy*amount;out[-1]-=dx*amount
 out=tuple(out);return out if not check or valid(out,sc,L) else None

def plan(sc,models,allow_clip=False,blocked=(),limit=80000):
 tree=topology(sc);L=limits(sc,allow_clip);start=tuple(sc['state']);goal=sc['goals'][0];h=lambda s:sum(abs(a-b) for a,b in zip(s[-2:],goal))/3;queue=[(h(start)*3,0,start,[])];cost={start:0};expanded=0
 while queue and expanded<limit:
  _,g,s,path=heapq.heappop(queue)
  if cost[s]!=g:continue
  expanded+=1
  if list(s[-2:])==goal:return path,dict(expanded=expanded)
  for k,m in sorted(models.items()):
   if (s,k) in blocked:continue
   nxt=predict(s,sc,tree,m['color'],m['mode'],m['amount'],L)
   if nxt is None or cost.get(nxt,10**9)<=g+1:continue
   cost[nxt]=g+1;heapq.heappush(queue,(g+1+3*h(nxt),g+1,nxt,path+[k]))
 return None,dict(expanded=expanded,frontier=len(queue),states=len(cost))


def render(sc,s,initial):
 f=[row[:] for row in initial];n=len(sc['bodies']);bg=max(set(v for row in f for v in row),key=lambda c:sum(row.count(c) for row in f))
 def rect(y,x,h,w,c):
  for yy in range(max(0,y),min(63,y+h)):
   for xx in range(max(0,x),min(64,x+w)):f[yy][xx]=c
 for i,b in enumerate(sc['bodies']):
  p=b['part'];dx,dy=b['root'];rect(p['y']-(dy<0),p['x']-(dx<0),p['h']+abs(dy),p['w']+abs(dx),bg)
 for p in sc['panels']:rect(p['y'],p['x'],p['h'],p['w'],bg)
 for i,b in enumerate(sc['bodies']):
  y,x,h,w,dx,dy=s[6*i:6*i+6];rect(y,x,h,w,b['color']);ry,rx=b['root_point'];rc=initial[ry][rx]
  if dx:rect(y,x-1 if dx<0 else x+w,3,1,rc)
  else:rect(y-1 if dy<0 else y+h,x,1,3,rc)
 for j,p in enumerate(sc['panels']):rect(*s[6*n+4*j:6*n+4*j+4],p['color'])
 y,x=s[-2:];rect(y,x,1,1,sc['marker'])
 for y,x in sc['goals']:
  for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]:rect(y+dy,x+dx,1,1,sc['marker'])
 for p in sc['controls']:
  for yy in range(p['y'],p['y']+p['h']):
   for xx in range(p['x'],p['x']+p['w']):f[yy][xx]=initial[yy][xx]
 return f

def matches(sc,s,initial,actual):return render(sc,s,initial)[:63]==actual[:63]
