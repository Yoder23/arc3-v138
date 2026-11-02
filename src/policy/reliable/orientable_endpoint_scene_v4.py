"""Observe separate assemblies, rotation-only obstacles and multiple partly-filled goals."""
from collections import Counter
from endpoint_visible_parts_v1 import parts
from orientable_endpoint_scene_v2 import key

def scene(o,roles=None):
 f=o['frame'];ps=parts(f);bg=Counter(v for row in f for v in row).most_common(1)[0][0];plus={(0,1),(1,0),(1,1),(1,2),(2,1)}
 glyphs=[p for p in ps if p['h']==p['w']==3 and (p['area']==7 or set(map(tuple,p['shape']))==plus)]
 boxes=[p for p in ps if p['h']>=5 and p['w']>=5 and p['area']==2*(p['h']+p['w'])-4 and any(p['y']<q['y']<p['y']+p['h'] and p['x']<q['x']<p['x']+p['w'] for q in glyphs)]
 mask={(y,x) for p in boxes for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w'])};buttons=[p for p in glyphs if (p['y'],p['x']) in mask];arrows=[p for p in buttons if p['area']==7];turns=[p for p in buttons if p['area']==5];colors=sorted({p['color'] for p in buttons})
 if not turns:return None
 goals=[];markers=set()
 for y in range(1,53):
  for x in range(1,63):
   c=f[y-1][x]
   if c not in colors+[bg] and all(f[y+dy][x+dx]==c for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]) and all(f[y+dy][x+dx]!=c for dy,dx in [(-1,-1),(-1,1),(1,-1),(1,1)]):goals.append([y,x]);markers.add(c)
 if len(goals)!=1 or len(markers)!=1:return None
 marker=next(iter(markers));bodies=[]
 for color in colors:
  coords=[(p['y']+y,p['x']+x) for p in ps if p['color']==color for y,x in p['shape'] if (p['y']+y,p['x']+x) not in mask]
  if not coords:return None
  y=min(a for a,b in coords);x=min(b for a,b in coords);h=max(a for a,b in coords)-y+1;w=max(b for a,b in coords)-x+1
  if h!=3 and w!=3:return None
  if not all(f[yy][xx] in (color,marker) for yy in range(y,y+h) for xx in range(x,x+w)):return None
  p=dict(y=y,x=x,h=h,w=w,color=color);roots=[]
  root_colors={q['color'] for q in ps if q['area']==3 and min(q['h'],q['w'])==1 and (q['y'],q['x']) not in mask}
  goal_mask={(gy+dy,gx+dx) for gy,gx in goals for dy,dx in [(0,0),(-1,0),(1,0),(0,-1),(0,1)]}
  choices=[]
  if h==3:choices.extend([([-1,0],y,x-1,[(y+j,x-1) for j in range(3)]),([1,0],y,x+w,[(y+j,x+w) for j in range(3)])])
  if w==3:choices.extend([([0,-1],y-1,x,[(y-1,x+j) for j in range(3)]),([0,1],y+h,x,[(y+h,x+j) for j in range(3)])])
  for root,ry,rx,line in choices:
   if not all(0<=yy<64 and 0<=xx<64 for yy,xx in line):continue
   visible={f[yy][xx] for yy,xx in line if (yy,xx) not in goal_mask}
   if len(visible)==1 and visible<=root_colors and all(f[yy][xx] in visible or (yy,xx) in goal_mask for yy,xx in line):roots.append(dict(root=root,point=[ry,rx]))
  if not roots:return None
  bodies.append(dict(color=color,part=p,candidates=roots))
 assignments=[]
 def bind(i,used,out):
  if i==len(bodies):assignments.append(out);return
  for q in bodies[i]['candidates']:
   k=tuple(q['point'])
   if k not in used:bind(i+1,used|{k},out+[q])
 bind(0,set(),[])
 if len(assignments)!=1:return None
 ends=[]
 for b,r in zip(bodies,assignments[0]):
  b['root']=r['root'];b['root_point']=r['point'];del b['candidates'];p=b['part'];dx,dy=b['root'];y=p['y']+1 if dy>=0 else p['y']+p['h']-2;x=p['x']+1 if dx>=0 else p['x']+p['w']-2
  if (roles is None and f[y][x]==marker) or (roles is not None and b['color'] in roles['end_colors']):
   if f[y][x]!=marker:return None
   ends.append(dict(color=b['color'],point=[y,x],marker=marker))
 if len(ends)!=len(goals):return None
 walls=[[p['y']+y,p['x']+x] for p in ps if p['color'] not in colors+[marker,bg] and p['area']>=9 for y,x in p['shape'] if p['y']+y<54 and (p['y']+y,p['x']+x) not in mask]
 state=tuple(v for b in bodies for v in [b['part'][k] for k in ['y','x','h','w']]+b['root'])+tuple(v for e in ends for v in e['point'])
 return dict(bodies=bodies,buttons=arrows,turns=turns,controls=boxes,endpoint=ends[0],roles=dict(end_colors=[e['color'] for e in ends]),goals=goals,walls=walls,state=state)
