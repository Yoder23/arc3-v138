"""Test whether a lateral particle front is stopped by another visible bar."""
from collections import deque
from beam_split_geometry_v10 import trace as old_trace
def boxes(s,poses):
 grouped={i for g in s.get('optical_groups',[])for i in g['indices']};result=[]
 for g in s.get('optical_groups',[]):
  q=[(*poses[i],*s['bars'][i]['box'][2:])for i in g['indices']];y=min(b[0]for b in q);x=min(b[1]for b in q)
  result.append((y,x,max(b[0]+b[2]for b in q)-y,max(b[1]+b[3]for b in q)-x))
 result.extend((*poses[i],*b['box'][2:])for i,b in enumerate(s['bars'])if i not in grouped)
 return result
def trace(s,poses):
 n=s['n'];dy,dx=s['source']['direction'];axis=s['axis'];rectangles=boxes(s,poses)
 todo=deque((p['position'][0],p['position'][1],0,0,-1)for p in s['sources']);seen=set();rays=set();hits=set();misses=set();splits=[]
 inside=lambda y,x,b:b[0]<=y<b[0]+b[2]and b[1]<=x<b[1]+b[3]
 while todo and len(seen)<4096:
  y,x,mode,d,owner=todo.popleft();y+=dy*n if mode==0 else(d*n if axis==1 else 0);x+=dx*n if mode==0 else(d*n if axis==0 else 0);state=y,x,mode,d,owner
  if not(0<=y<64 and 0<=x<64)or state in seen:continue
  seen.add(state);rays.add((y,x))
  if mode:
   if any(i!=owner and inside(y,x,b)for i,b in enumerate(rectangles)):continue
   b=rectangles[owner];cross=1-axis;value=(y,x)[cross]
   todo.append((y,x,1,d,owner)if b[cross]<=value<b[cross]+b[cross+2]else(y,x,0,0,-1));continue
  stopped=False
  for i,g in enumerate(s['goals']):
   if inside(y,x,g['object']['box']):
    (hits if(y,x)==tuple(g['opening'])else misses).add(i);stopped=True;break
  if stopped:continue
  for i,b in enumerate(rectangles):
   if not inside(y,x,b):continue
   start=y-dy*n,x-dx*n
   if not any(j!=i and inside(*start,q)for j,q in enumerate(rectangles)):
    todo.extend([(start[0],start[1],1,-1,i),(start[0],start[1],1,1,i)])
   splits.append(dict(index=i,entry=(y,x),children=[]));stopped=True;break
  if not stopped:todo.append((y,x,0,0,-1))
 return dict(hits=sorted(hits),misses=sorted(misses),rays=sorted(rays),splits=splits)

def compare(s,before,after):
 from beam_compound_optics_v2 import observed_tiles
 n=s['n'];axis=s['axis'];direction=s['source']['direction'][axis];skip={b['box'][axis]-direction*n for b in s['bars']};poses=[b['box'][:2]for b in s['bars']];actual=observed_tiles(s,after)
 domain={(y,x)for y in range(s['origin'][0],64-n+1,n)for x in range(s['origin'][1],64-n+1,n)if(y,x)[axis]not in skip and all(before[yy][xx]==s['background']for yy in range(y,y+n)for xx in range(x,x+n))}
 old=sorted(({tuple(q)for q in old_trace(s,poses)['rays']}^actual)&domain);new=sorted(({tuple(q)for q in trace(s,poses)['rays']}^actual)&domain)
 return dict(jump_model_error=old,front_model_error=new,adopt=len(new)<len(old),interpretation='intermediate horizontal particle paths can collide with other visible bars')
