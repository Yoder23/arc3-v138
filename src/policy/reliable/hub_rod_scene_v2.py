"""Observe duplicate colored rods around a rotatable hub, endpoints and attached panels."""
from collections import Counter
from endpoint_visible_parts_v1 import parts
from orientable_endpoint_scene_v2 import key

def scene(o):
 f=o['frame'];ps=parts(f);bg=Counter(v for row in f for v in row).most_common(1)[0][0];plus={(0,1),(1,0),(1,1),(1,2),(2,1)}
 glyphs=[p for p in ps if p['h']==p['w']==3 and (p['area']==7 or set(map(tuple,p['shape']))==plus)]
 controls=[p for p in ps if p['h']>=5 and p['w']>=5 and p['area']==2*(p['h']+p['w'])-4 and any(p['y']<q['y']<p['y']+p['h'] and p['x']<q['x']<p['x']+p['w'] for q in glyphs)]
 cm={(y,x) for p in controls for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w'])};buttons=[p for p in glyphs if (p['y'],p['x']) in cm];arrows=[p for p in buttons if p['area']==7];turns=[p for p in buttons if p['area']==5];colors=sorted({p['color'] for p in arrows})
 hubs=[p for p in ps if p['h']==p['w']==3 and p['area']==9 and p['color'] in {q['color'] for q in turns} and (p['y'],p['x']) not in cm]
 if len(hubs)!=1:return None
 hub=hubs[0];cy,cx=hub['y']+1,hub['x']+1;goals=[];markers=set()
 for y in range(1,53):
  for x in range(1,63):
   c=f[y-1][x]
   if (y,x) not in cm and c not in colors+[bg] and all(f[y+dy][x+dx]==c for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]) and all(f[y+dy][x+dx]!=c for dy,dx in [(-1,-1),(-1,1),(1,-1),(1,1)]):goals.append([y,x]);markers.add(c)
 if len(goals)!=1 or len(markers)!=1:return None
 marker=next(iter(markers));gm={(y+dy,x+dx) for y,x in goals for dy,dx in [(0,0),(-1,0),(1,0),(0,-1),(0,1)]};bodies=[]
 roots=[p for p in ps if p['area']==3 and min(p['h'],p['w'])==1 and (p['y'],p['x']) not in cm]
 for q in roots:
  for sign in (-1,1):
   vertical=q['h']==1;start=q['y'] if vertical else q['x'];cross=q['x'] if vertical else q['y'];coords=[];color=None;end=None
   for d in range(1,65):
    z=start+sign*d;line=[(z,cross+j) if vertical else (cross+j,z) for j in range(3)]
    if not all(0<=y<63 and 0<=x<64 for y,x in line):break
    vals=[f[y][x] for y,x in line]
    if color is None:
     cs=[c for c in colors if vals.count(c)>=2]
     if len(cs)!=1:break
     color=cs[0]
    if not all(v in (color,marker) or xy in cm for xy,v in zip(line,vals)):break
    coords+=line
    marked=[xy for xy,v in zip(line,vals) if v==marker and xy not in gm]
    if marked:end=list(marked[0])
   if len(coords)<6:continue
   y=min(a for a,b in coords);x=min(b for a,b in coords);h=max(a for a,b in coords)-y+1;w=max(b for a,b in coords)-x+1;root=[0,-sign] if vertical else [-sign,0];near=abs(q['y']+(q['h']//2)-cy)+abs(q['x']+(q['w']//2)-cx)==2
   bodies.append(dict(id=str(color)+('h' if near else 'e'),color=color,part=dict(y=y,x=x,h=h,w=w),root=root,root_point=[q['y'],q['x']],hub=near,endpoint=end));break
 if len(bodies)<=len(colors) or len({b['id'] for b in bodies})!=len(bodies) or sum(b['hub'] for b in bodies)!=4:return None
 bodies.sort(key=lambda b:b['id']);ends=[dict(body=b['id'],point=b['endpoint']) for b in bodies if b['endpoint']]
 if len(ends)!=1:return None
 panels=[]
 for p in ps:
  if p['color'] in colors+[bg,marker] or p in controls or p['area']!=p['h']*p['w'] or min(p['h'],p['w'])!=3 or max(p['h'],p['w'])<8:continue
  for b in bodies:
   r=b['part'];dx,dy=b['root']
   if r['h']==3 and p['w']==3 and p['y']==r['y'] and ((dx>0 and p['x']+3==r['x']) or (dx<0 and p['x']==r['x']+r['w'])):
    panels.append(dict(color=p['color'],y=p['y'],x=p['x'],h=p['h'],w=p['w'],body=b['id']));break
 pm={(y,x) for p in panels for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w'])}
 walls=[[p['y']+y,p['x']+x] for p in ps if p['color'] not in colors+[bg,marker,hub['color']] and p['area']>=9 for y,x in p['shape'] if (p['y']+y,p['x']+x) not in cm|pm and p['y']+y<54]
 state=tuple(v for b in bodies for v in [b['part'][k] for k in ['y','x','h','w']]+b['root'])+tuple(v for p in panels for v in [p[k] for k in ['y','x','h','w']])+tuple(ends[0]['point'])
 return dict(bodies=bodies,buttons=arrows,turns=turns,hub=hub,ends=ends,goals=goals,marker=marker,controls=controls,panels=panels,walls=walls,state=state)
