"""A movable concave corner may turn a particle through its missing tile."""
from collections import deque
from beam_split_geometry_v16 import trace as old_trace
from binary_demonstration_bootstrap_v1 import components
from beam_compound_optics_v2 import observed_tiles
from beam_front_collision_v1 import boxes
def objects(frame,n):
 result=[]
 for o in components(frame):
  y,x,h,w=o['box']
  if(h,w)!=(2*n,2*n)or len(o['shape'])!=3*n*n:continue
  cells=set(o['shape']);tiles=[(dy,dx)for dy in(0,n)for dx in(0,n)if all((yy,xx)in cells for yy in range(dy,dy+n)for xx in range(dx,dx+n))]
  if len(tiles)==3:result.append(dict(o,corner_missing=next(q for q in[(0,0),(0,n),(n,0),(n,n)]if q not in tiles)))
 return result
def trace(s,poses):
 n=s['n'];indices=[i for i,b in enumerate(s['bars'])if 'corner_missing'not in b];remap={i:j for j,i in enumerate(indices)}
 plain=dict(s,bars=[s['bars'][i]for i in indices],optical_groups=[dict(g,indices=[remap[i]for i in g['indices']])for g in s.get('optical_groups',[])if all(i in remap for i in g['indices'])]);rects=boxes(plain,[poses[i]for i in indices])
 corners=[(i,(*poses[i],*b['box'][2:]),b['corner_missing'])for i,b in enumerate(s['bars'])if 'corner_missing'in b]
 inside=lambda y,x,b:b[0]<=y<b[0]+b[2]and b[1]<=x<b[1]+b[3]
 sources=[tuple(p['position'])for p in s['sources']]
 for e in s.get('moving_emitters',[]):sources.append(tuple(a+b for a,b in zip(poses[e['anchor']],e['offset'])))
 vy,vx=s['source']['direction'];todo=deque((y,x,vy,vx,0,0,-1)for y,x in sources);seen=set();rays=set();hits=set();misses=set();splits=[];turns=[]
 while todo and len(seen)<4096:
  y,x,dy,dx,mode,d,owner=todo.popleft();axis=0 if dy else 1
  y+=dy*n if not mode else(d*n if axis==1 else 0);x+=dx*n if not mode else(d*n if axis==0 else 0)
  state=(y,x,dy,dx,mode,d,owner)
  if not(0<=y<64 and 0<=x<64)or state in seen:continue
  seen.add(state);rays.add((y,x));caught=False
  travel=(dy,dx)if not mode else((d,0)if axis==1 else(0,d))
  for i,b,missing in corners:
   my,mx=missing;point=(b[0]+my,b[1]+mx)
   if(y,x)==point:
    exits=[(-1 if my==0 else 1,0),(0,-1 if mx==0 else 1)];direction=None
    for k,v in enumerate(exits):
     if travel==(-v[0],-v[1]):direction=exits[1-k]
    if direction:todo.append((y,x,*direction,0,0,-1));turns.append(dict(index=i,point=point,incoming=travel,outgoing=direction))
    caught=True;break
   if inside(y,x,b):caught=True;break
  if caught:continue
  if mode:
   collision=next((i for i,b in enumerate(rects)if i!=owner and inside(y,x,b)),None)
   if collision is not None:
    if s.get('front_mode')!='stop':todo.extend([(y-dy*n,x-dx*n,dy,dx,1,-1,collision),(y-dy*n,x-dx*n,dy,dx,1,1,collision)])
    continue
   b=rects[owner];cross=1-axis;value=(y,x)[cross]
   todo.append((y,x,dy,dx,1,d,owner)if b[cross]<=value<b[cross]+b[cross+2]else(y,x,dy,dx,0,0,-1));continue
  for i,g in enumerate(s['goals']):
   if inside(y,x,g['object']['box']):(hits if(y,x)==tuple(g['opening'])else misses).add(i);caught=True;break
  if caught:continue
  for i,b in enumerate(rects):
   if not inside(y,x,b):continue
   if b[axis+2]==n:
    start=y-dy*n,x-dx*n
    if s.get('front_mode')!='stop'or not any(j!=i and inside(*start,q)for j,q in enumerate(rects)):
     todo.extend([(start[0],start[1],dy,dx,1,-1,i),(start[0],start[1],dy,dx,1,1,i)])
    splits.append(dict(index=i,entry=(y,x),children=[]))
   caught=True;break
  if not caught:todo.append((y,x,dy,dx,0,0,-1))
 result=dict(hits=sorted(hits),misses=sorted(misses),rays=sorted(rays),splits=splits,turns=turns)
 if s.get('connected_source_goal')and s.get('moving_emitters'):
  external=trace(dict(s,moving_emitters=[]),poses);paths=set(map(tuple,external['rays']));dy,dx=s['source']['direction'];marks=[(poses[q['anchor']][0]+q['offset'][0]-dy*n,poses[q['anchor']][1]+q['offset'][1]-dx*n)for q in s['moving_emitters']]
  result.update(joint_hits=[i for i,p in enumerate(marks)if p in paths],joint_targets=marks)
 return result
def compare(s,before,after):
 if not any('corner_missing'in b for b in s['bars'])or len(after.get('animation_frames',[]))<=1:return None
 poses=[b['box'][:2]for b in s['bars']];new=trace(s,poses);idx=[i for i,b in enumerate(s['bars'])if 'corner_missing'not in b]
 old=old_trace(dict(s,bars=[s['bars'][i]for i in idx],optical_groups=[],moving_emitters=[]),[poses[i]for i in idx]);actual=observed_tiles(s,after);n=s['n'];domain={(y,x)for y in range(s['origin'][0],64-n+1,n)for x in range(s['origin'][1],64-n+1,n)if all(before[yy][xx]==s['background']for yy in range(y,y+n)for xx in range(x,x+n))}
 errors={key:sorted(({tuple(v)for v in p['rays']}^actual)&domain)for key,p in [('ignored',old),('corner',new)]}
 return dict(errors=errors,turns=new['turns'],adopt=len(errors['corner'])<len(errors['ignored']),hypothesis='incoming_particle_turns_between_the_two_open_sides_of_a_visible_missing_corner_tile')
