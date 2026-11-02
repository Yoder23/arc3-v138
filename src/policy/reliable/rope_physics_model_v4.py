"""Visible lattice hypothesis: carrying, collision pushes and rail constraints."""
from rope_visible_parts_v1 import parts

def scene(o):
 ps=parts(o['frame']);hs=[p for p in ps if p['h']==p['w']==6 and p['area']==18 and p['y']<50]
 if len(hs)!=1:return None
 h=hs[0];items=sorted([p for p in ps if p['h']==p['w']==4 and p['area']==16 and p['y']<50],key=lambda p:p['color'])
 fields=[p for p in ps if p['y']<50 and p['h']>=12 and p['w']>=12 and p['area']>=200]
 if not fields:return None
 f=max(fields,key=lambda p:p['area']);tip=max((p['x']+x for p in ps if p['color']==1 and h['y']<=p['y']<h['y']+6 for y,x in p['shape']),default=h['x']+5)
 rails=[]
 for x in range(f['x'],f['x']+f['w']-1):
  ys=[y for y in range(3,50) if set(o['frame'][y][x:x+2])=={2,3}]
  if len(ys)>=8 and max(ys)-min(ys)>=12:rails.append((x-1,min(ys),max(ys)))
 return dict(state=(h['y'],tip,*[v for p in items for v in (p['y'],p['x'])]),colors=[p['color'] for p in items],head=h,items=items,rails=rails,bounds=(f['y'],f['y']+f['h']-6,h['x']+7,f['x']+f['w']-5),tipbounds=(h['x']+5,f['x']+f['w']-1))

def step(s,a,c):
 y,t,*v=s;pts=[list(v[i:i+2]) for i in range(0,len(v),2)];lo,hi,xlo,xhi=c['bounds'];tlo,thi=c['tipbounds'];old=[p[:] for p in pts]
 def push(i,dy,dx,stack=()):
  if i in stack:return False
  py,px=pts[i];ny,nx=py+dy,px+dx
  if ny<lo+1 or ny>hi+1 or nx<xlo or nx>xhi:return False
  if dx and any((px==rx or nx==rx) and top<=py<=bottom for rx,top,bottom in c['rails']):return False
  for j,p in enumerate(pts):
   if j!=i and p==[ny,nx] and not push(j,dy,dx,stack+(i,)):return False
  pts[i]=[ny,nx];return True
 if a in (3,4):
  dx=6 if a==4 else -6;nt=max(tlo,min(thi,t+dx))
  if nt==t:return s
  order=sorted([i for i,p in enumerate(old) if p[0]==y+1 and p[1]<=t-4],key=lambda i:old[i][1],reverse=a==4)
  moved=set()
  for i in order:
   if pts[i]!=old[i]:continue
   snapshot=[p[:] for p in pts]
   if not push(i,0,dx):pts=snapshot
  t=nt
 elif a in (1,2):
  dy=-6 if a==1 else 6
  if not lo<=y+dy<=hi:return s
  order=sorted([i for i,p in enumerate(old) if p[1]<=t-4 and p[0] in (y+1,y+dy+1)],key=lambda i:old[i][0],reverse=dy>0)
  # Objects in the destination row are pushed by the rope even without an attached source.
  for i in order:
   if pts[i]!=old[i]:continue
   if not push(i,dy,0):return s
  y+=dy
 return (y,t,*[v for p in pts for v in p])
