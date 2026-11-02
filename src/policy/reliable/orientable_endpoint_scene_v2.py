"""Observe articulated rods and distinct extension/orientation controls."""
from collections import Counter
from endpoint_visible_parts_v1 import parts
from coupled_rods_scene_v12 import key

def scene(o):
 f=o['frame'];ps=parts(f);bg=Counter(v for row in f for v in row).most_common(1)[0][0]
 arrows=[p for p in ps if p['h']==p['w']==3 and p['area']==7];colors=sorted({p['color'] for p in arrows})
 boxes=[p for p in ps if p['h']>=5 and p['w']>=5 and p['area']==2*(p['h']+p['w'])-4 and any(p['y']<q['y']<p['y']+p['h'] and p['x']<q['x']<p['x']+p['w'] for q in ps if q['color'] in colors and q['h']==q['w']==3 and q['area'] in (5,7))]
 mask={(y,x) for p in boxes for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w'])};turns=[p for p in ps if p['color'] in colors and p['h']==p['w']==3 and p['area']==5 and (p['y'],p['x']) in mask]
 if len(turns)!=len(colors) or len(colors)<2:return None
 bodies=[];ends=[]
 for color in colors:
  cs=[p for p in ps if p['color']==color and (p['h']==3 or p['w']==3) and p['area']>=5 and (p['y'],p['x']) not in mask]
  if len(cs)!=1:return None
  p=cs[0];holes=[(y,x,f[y][x]) for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w']) if f[y][x]!=color]
  if len(holes)>1:return None
  if holes:ends.append(dict(color=color,point=list(holes[0][:2]),marker=holes[0][2]))
  roots=[]
  for q in ps:
   if q['area']!=3 or q['color']==color or (q['y'],q['x']) in mask:continue
   if q['h']==3 and q['w']==1 and p['h']==3 and q['y']==p['y']:
    if q['x']+1==p['x']:roots.append(dict(root=[-1,0],point=[q['y'],q['x']]))
    elif p['x']+p['w']==q['x']:roots.append(dict(root=[1,0],point=[q['y'],q['x']]))
   if q['h']==1 and q['w']==3 and p['w']==3 and q['x']==p['x']:
    if q['y']+1==p['y']:roots.append(dict(root=[0,-1],point=[q['y'],q['x']]))
    elif p['y']+p['h']==q['y']:roots.append(dict(root=[0,1],point=[q['y'],q['x']]))
  if not roots:return None
  bodies.append(dict(color=color,part=p,root_candidates=roots))
 assignments=[]
 def bind(i,used,assignment):
  if i==len(bodies):assignments.append(assignment);return
  for root in bodies[i]['root_candidates']:
   k=tuple(root['point'])
   if k not in used:bind(i+1,used|{k},assignment+[root])
 bind(0,set(),[])
 if len(assignments)!=1:return None
 for b,r in zip(bodies,assignments[0]):b['root']=r['root'];b['root_point']=r['point'];del b['root_candidates']
 if len(ends)!=1:return None
 marker=ends[0]['marker'];goals=[[y,x] for y in range(1,53) for x in range(1,63) if all(f[y+dy][x+dx]==marker for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]) and all(f[y+dy][x+dx]!=marker for dy,dx in [(-1,-1),(-1,1),(1,-1),(1,1)])]
 if len(goals)!=1:return None
 walls=[[p['y']+y,p['x']+x] for p in ps if p['color'] not in colors+[marker,bg] and p['area']>=9 for y,x in p['shape'] if p['y']+y<54 and (p['y']+y,p['x']+x) not in mask]
 state=tuple(v for b in bodies for v in [b['part'][k] for k in ['y','x','h','w']]+b['root'])+tuple(ends[0]['point'])
 return dict(bodies=bodies,buttons=arrows,turns=turns,controls=boxes,endpoint=ends[0],goals=goals,walls=walls,state=state)
