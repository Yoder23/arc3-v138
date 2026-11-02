from collections import Counter
import heapq
from endpoint_visible_parts_v1 import parts
def key(p):return str(p['color'])+':'+str(tuple(map(tuple,p['shape'])))
def scene(obs,roles=None):
 ps=parts(obs['frame']);f=obs['frame'];background=Counter(v for row in f for v in row).most_common(1)[0][0];buttons=[p for p in ps if p['h']==p['w']==3 and p['area']==7];colors=sorted({p['color'] for p in buttons});bodies=[];endpoint=None;marker=None;goals=[]
 for y in range(1,53):
  for x in range(1,63):
   c=f[y-1][x]
   if c!=background and c not in colors and f[y][x]!=c and all(f[y+dy][x+dx]==c for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]):goals.append([y,x]);marker=c
 if len(goals)!=1:return None
 goal_mask={(y+dy,x+dx) for y,x in goals for dy,dx in [(0,0),(-1,0),(1,0),(0,-1),(0,1)]}
 controls=[p for p in ps if p['h']==7 and p['w']==13 and p['area']==36 and any(p['y']<=b['y']<p['y']+7 and p['x']<=b['x']<p['x']+13 for b in buttons)]
 control_mask={(y,x) for p in controls for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w'])}
 learned={}
 for q in ps:
  if q['area']!=3 or q['y']>=54 or min(q['h'],q['w'])!=1:continue
  rolekey=('h:'+str(q['y'])) if q['h']==1 else ('v:'+str(q['x']))
  for sign in (-1,1):
   if roles is not None and (rolekey not in roles or sign!=roles[rolekey]['sign']):continue
   vertical=q['h']==1;start=q['y'] if vertical else q['x'];cross=q['x'] if vertical else q['y'];lines=[];color=None;end=None
   for d in range(1,63):
    z=start+sign*d;coords=[(z,cross+j) if vertical else (cross+j,z) for j in range(3)]
    if not all(0<=yy<54 and 0<=xx<63 for yy,xx in coords):break
    vals=[f[yy][xx] for yy,xx in coords]
    if color is None:
     choices=[c for c in colors if vals.count(c)>=2]
     if len(choices)!=1:break
     color=choices[0]
     if roles is not None and color!=roles[rolekey]['color']:break
    if not all(v in (color,marker) for v in vals):break
    lines+=coords
    marked=[coord for coord,v in zip(coords,vals) if v==marker and coord not in goal_mask]
    if marked:
     end=list(marked[0]);z+=sign;cap=[(z,cross+j) if vertical else (cross+j,z) for j in range(3)]
     if all(0<=yy<54 and 0<=xx<63 and f[yy][xx]==color for yy,xx in cap):lines+=cap
     break
   if len(lines)<6:continue
   top=min(y for y,x in lines);left=min(x for y,x in lines);bottom=max(y for y,x in lines);right=max(x for y,x in lines);shape=tuple((y-top,x-left) for y,x in sorted(lines) if f[y][x]==color);p=dict(color=color,y=top,x=left,h=bottom-top+1,w=right-left+1,area=len(shape),shape=shape);root=[0,-sign] if vertical else [-sign,0];bodies.append(dict(color=color,part=p,root=root,root_point=[q['y'],q['x']],is_endpoint=(roles[rolekey]['is_endpoint'] if roles is not None else bool(end))));learned[rolekey]=dict(color=color,sign=sign,is_endpoint=bodies[-1]['is_endpoint'])
   if end and bodies[-1]['is_endpoint']:endpoint=end
 if endpoint is None or len(bodies)<=len(colors):return None
 for color in colors:
  group=[b for b in bodies if b['color']==color]
  if len(group)<2:continue
  marked=[b for b in group if b['is_endpoint']]
  if len(marked)!=1:continue
  ref=marked[0];length=ref['part']['w'] if ref['root'][0] else ref['part']['h']
  for b in group:
   ry,rx=b['root_point'];dx,dy=b['root'];y=ry if dx else (ry-length if dy>0 else ry+1);x=rx if dy else (rx-length if dx>0 else rx+1);h=3 if dx else length;ww=length if dx else 3
   coords=[(yy,xx) for yy in range(y,y+h) for xx in range(x,x+ww)]
   if not all(0<=yy<64 and 0<=xx<64 and (f[yy][xx]==color or f[yy][xx]==marker or (yy,xx) in control_mask) for yy,xx in coords):return None
   shape=tuple((yy-y,xx-x) for yy,xx in coords if f[yy][xx]==color);b['part']=dict(color=color,y=y,x=x,h=h,w=ww,area=len(shape),shape=shape);b['control_occlusion']=[list(q) for q in coords if q in control_mask]
 bodies.sort(key=lambda b:(b['color'],b['root'],b['part']['x'] if b['part']['h']==3 else b['part']['y']))
 walls=[]
 for p in ps:
  if p not in controls and p['y']<54 and p['color'] not in colors+[marker,background] and p['area']>=20 and max(p['h'],p['w'])>=8:walls.extend([[p['y']+y,p['x']+x] for y,x in p['shape']])
 state=tuple(v for b in bodies for v in [b['part'][k] for k in ['y','x','h','w']])+tuple(endpoint)
 return dict(bodies=bodies,buttons=buttons,endpoint=endpoint,marker=marker,goals=goals,walls=walls,roles=learned,controls=controls,state=state)
def valid(state,sc):
 rects=[];wall=set(map(tuple,sc['walls']))
 for i,b in enumerate(sc['bodies']):
  y,x,h,w=state[4*i:4*i+4]
  if min(h,w)<2 or y<0 or x<0 or y+h>=54 or x+w>=63 or (h!=3 and w!=3):return False
  rx,ry=b['root'];top=y-(ry<0);left=x-(rx<0);bottom=y+h+(ry>0);right=x+w+(rx>0)
  if any(top<=yy<bottom and left<=xx<right for yy,xx in wall):return False
  if any(max(top,a)<min(bottom,c) and max(left,b)<min(right,d) for a,b,c,d in rects):return False
  rects.append((top,left,bottom,right))
 return True
def plan(sc,models,blocked=()):
 if len(sc['goals'])!=1:return None
 start=tuple(sc['state']);goal=sc['goals'][0];h=lambda s:(abs(s[-2]-goal[0])+abs(s[-1]-goal[1]))/3;queue=[(h(start),0,start,[])];cost={start:0};expanded=0
 while queue and expanded<60000:
  _,g,s,path=heapq.heappop(queue)
  if g!=cost[s]:continue
  expanded+=1
  if list(s[-2:])==goal:return path
  for k,m in sorted(models.items()):
   if len(m['support'])<2 or len(m['delta'])!=len(s) or (s,k) in blocked:continue
   nxt=tuple(a+b for a,b in zip(s,m['delta']))
   if not valid(nxt,sc) or cost.get(nxt,10**9)<=g+1:continue
   cost[nxt]=g+1;heapq.heappush(queue,(g+1+h(nxt),g+1,nxt,path+[k]))
 return None
