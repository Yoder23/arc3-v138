"""Bind visible root identities, filled goals and attached panels in a common state."""
from collections import Counter
import heapq,itertools
from endpoint_visible_parts_v1 import parts
from coupled_rods_scene_v12 import key

def scene(obs,roles=None,templates=None):
 f=obs['frame'];ps=parts(f);bg=Counter(v for row in f for v in row).most_common(1)[0][0];buttons=[p for p in ps if p['h']==p['w']==3 and p['area']==7];colors=sorted({p['color'] for p in buttons});goals=[];markers=set()
 for y in range(1,53):
  for x in range(1,63):
   c=f[y-1][x]
   if c!=bg and c not in colors and all(f[y+dy][x+dx]==c for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]) and all(f[y+dy][x+dx]!=c for dy,dx in [(-1,-1),(-1,1),(1,-1),(1,1)]):goals.append([y,x]);markers.add(c)
 if len(goals)<2 or len(markers)!=1:return None
 marker=next(iter(markers));gm={(y+dy,x+dx) for y,x in goals for dy,dx in [(0,0),(-1,0),(1,0),(0,-1),(0,1)]}
 controls=[p for p in ps if p['h']>=5 and p['w']>=9 and p['area']==2*(p['h']+p['w'])-4 and sum(p['y']<b['y']<p['y']+p['h'] and p['x']<b['x']<p['x']+p['w'] for b in buttons)>=2]
 cm={(y,x) for p in controls for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w'])}
 roots=[p for p in ps if p['area']==3 and p['y']<54 and min(p['h'],p['w'])==1 and (p['y'],p['x']) not in cm];counts=Counter();bodies=[];learned={}
 for q in sorted(roots,key=lambda p:(p['y'],p['x'])):
  base=('h:'+str(q['y'])) if q['h']==1 else ('v:'+str(q['x']));rk=base+':'+str(counts[base]);counts[base]+=1
  for sign in (-1,1):
   if roles is not None and (rk not in roles or sign!=roles[rk]['sign']):continue
   vertical=q['h']==1;start=q['y'] if vertical else q['x'];cross=q['x'] if vertical else q['y'];coords=[];color=None
   for d in range(1,64):
    z=start+sign*d;line=[(z,cross+j) if vertical else (cross+j,z) for j in range(3)]
    if not all(0<=yy<54 and 0<=xx<64 for yy,xx in line):break
    vals=[f[yy][xx] for yy,xx in line]
    if color is None:
     choices=[c for c in colors if vals.count(c)>=2]
     if len(choices)!=1:break
     color=choices[0]
     if roles is not None and color!=roles[rk]['color']:break
    if not all(v in (color,marker) for v in vals):break
    coords+=line
    if any(v==marker and xy not in gm for v,xy in zip(vals,line)):
     cap=[(z+sign,cross+j) if vertical else (cross+j,z+sign) for j in range(3)]
     if all(0<=yy<54 and 0<=xx<64 and f[yy][xx]==color for yy,xx in cap):coords+=cap
     break
   if len(coords)<6:continue
   y=min(a for a,b in coords);x=min(b for a,b in coords);h=max(a for a,b in coords)-y+1;w=max(b for a,b in coords)-x+1;root=[0,-sign] if vertical else [-sign,0]
   tip=[(y+h-2 if sign>0 else y+1),x+1] if vertical else [y+1,(x+w-2 if sign>0 else x+1)]
   endpoint=roles[rk]['is_endpoint'] if roles is not None else f[tip[0]][tip[1]]==marker
   if endpoint and f[tip[0]][tip[1]]!=marker:return None
   learned[rk]=dict(color=color,sign=sign,is_endpoint=endpoint)
   bodies.append(dict(id=rk,color=color,root=root,root_point=[q['y'],q['x']],is_endpoint=endpoint,part=dict(y=y,x=x,h=h,w=w)))
   break
 if len(bodies)<=len(colors):return None
 for color in colors:
  group=[b for b in bodies if b['color']==color];marked=[b for b in group if b['is_endpoint']]
  if len(group)<2 or len(marked)!=1:continue
  ref=marked[0];length=ref['part']['w' if ref['root'][0] else 'h']
  for b in group:
   ry,rx=b['root_point'];dx,dy=b['root'];y=ry if dx else (ry-length if dy>0 else ry+1);x=rx if dy else (rx-length if dx>0 else rx+1);h=3 if dx else length;w=length if dx else 3
   if not all(0<=yy<64 and 0<=xx<64 and (f[yy][xx] in (color,marker) or (yy,xx) in cm) for yy in range(y,y+h) for xx in range(x,x+w)):return None
   b['part']=dict(y=y,x=x,h=h,w=w)
 bodies.sort(key=lambda b:b['id']);ends=[]
 for b in bodies:
  if b['is_endpoint']:
   p=b['part'];dx,dy=b['root'];y=p['y']+1 if dy>=0 else p['y']+p['h']-2;x=p['x']+1 if dx>=0 else p['x']+p['w']-2;ends.append(dict(body=b['id'],point=[y,x]))
 if len(ends)!=len(goals):return None
 if templates is None:
  templates=[]
  for p in ps:
   if p['y']>=54 or p['color'] in colors+[marker,bg] or p in controls or p['area']!=p['h']*p['w'] or min(p['h'],p['w'])!=3 or max(p['h'],p['w'])<8:continue
   candidates=[b for b in bodies if (p['w']==3 and b['part']['h']==3 and b['part']['x']==p['x']+3 and b['part']['y']==p['y']) or (p['h']==3 and b['part']['w']==3 and b['part']['y']==p['y']+3 and b['part']['x']==p['x'])]
   if len(candidates)==1:
    b=candidates[0];templates.append(dict(color=p['color'],h=p['h'],w=p['w'],body=b['id'],dy=p['y']-b['part']['y'],dx=p['x']-b['part']['x']))
 panels=[];pm=set()
 for t in templates:
  b=next((b for b in bodies if b['id']==t['body']),None)
  if b is None:return None
  p=dict(color=t['color'],y=b['part']['y']+t['dy'],x=b['part']['x']+t['dx'],h=t['h'],w=t['w']);coords={(y,x) for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w'])}
  if not all(0<=y<64 and 0<=x<64 and (f[y][x]==p['color'] or (y,x) in gm or (y,x) in cm) for y,x in coords):return None
  panels.append(p);pm|=coords
 walls=[]
 for p in ps:
  if p['y']<54 and p not in controls and p['color'] not in colors+[marker,bg] and p['area']>=9:
   walls.extend([p['y']+y,p['x']+x] for y,x in p['shape'] if (p['y']+y,p['x']+x) not in pm and (p['y']+y,p['x']+x) not in cm)
 state=tuple(v for b in bodies for v in [b['part'][k] for k in ['y','x','h','w']])+tuple(v for p in panels for v in [p[k] for k in ['y','x','h','w']])+tuple(v for e in ends for v in e['point'])
 return dict(bodies=bodies,buttons=buttons,ends=ends,goals=goals,marker=marker,roles=learned,templates=templates,panels=panels,walls=walls,controls=controls,state=state)

def valid(s,sc):
 boxes=[];walls=set(map(tuple,sc['walls']))
 for i,b in enumerate(sc['bodies']+sc['panels']):
  y,x,h,w=s[4*i:4*i+4]
  if min(h,w)<2 or y<0 or x<0 or y+h>=54 or x+w>=64:return False
  dx,dy=b.get('root',[0,0]);box=(y-(dy<0),x-(dx<0),y+h+(dy>0),x+w+(dx>0))
  if any(box[0]<=yy<box[2] and box[1]<=xx<box[3] for yy,xx in walls):return False
  if any(max(box[0],q[0])<min(box[2],q[2]) and max(box[1],q[1])<min(box[3],q[3]) for q in boxes):return False
  boxes.append(box)
 return True

def plan(sc,models,blocked=()):
 n=len(sc['ends']);goals=[tuple(v for p in q for v in p) for q in itertools.permutations(sc['goals'])];offset=len(sc['state'])-2*n
 def h(s):return min(sum(abs(a-b) for a,b in zip(s[offset:],g))/3 for g in goals)
 start=tuple(sc['state']);queue=[(2*h(start),0,start,[])];cost={start:0};expanded=0
 while queue and expanded<70000:
  _,g,s,path=heapq.heappop(queue)
  if g!=cost[s]:continue
  expanded+=1
  if s[offset:] in goals:return path
  for k,m in sorted(models.items()):
   if len(m['support'])<2 or len(m['delta'])!=len(s) or (s,k) in blocked:continue
   nxt=tuple(a+b for a,b in zip(s,m['delta']))
   if cost.get(nxt,10**9)<=g+1 or not valid(nxt,sc):continue
   cost[nxt]=g+1;heapq.heappush(queue,(g+1+2*h(nxt),g+1,nxt,path+[k]))
 return None
