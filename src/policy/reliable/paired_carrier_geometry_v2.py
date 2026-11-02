"""Place a visible carrier pair beside a peg, then ask for legal landing feedback."""
import copy
from collections import Counter,deque
from binary_demonstration_bootstrap_v1 import components as objects
from fused_peg_carriers_v1 import scan
def scene(frame):
 solid=[o for o in objects(frame) if not o.get('parts') and o['box'][2]==o['box'][3] and 2<=o['box'][2]<=8 and len(o['shape'])==o['box'][2]**2]
 groups=Counter((o['ink'],o['box'][2]) for o in solid)
 if not groups:return None
 (field,size),n=groups.most_common(1)[0]
 if n<6:return None
 seeds=[o['box'][:2] for o in solid if o['ink']==field and o['box'][2]==size]
 diffs=[abs(a[1]-b[1]) for a in seeds for b in seeds if a[0]==b[0] and size<abs(a[1]-b[1])<=size*3]
 if not diffs:return None
 pitch=min(diffs);oy=min(y for y,x in seeds)%pitch;ox=min(x for y,x in seeds)%pitch;cells=[]
 for y in range(oy,65-size,pitch):
  for x in range(ox,65-size,pitch):
   if all(frame[y+dy][x+dx]==field for dy,dx in ((0,0),(0,size-1),(size-1,0),(size-1,size-1))):cells.append((y,x))
 cores=Counter(frame[y+(size-1)//2][x+(size-1)//2] for y,x in cells if frame[y+(size-1)//2][x+(size-1)//2]!=field)
 if not cores:return None
 mark=cores.most_common(1)[0][0]
 return dict(cells=cells,pitch=pitch,size=size,field=field,mark=mark)

def positions(frame,size,ink):return tuple((b['box'][0]+1,b['box'][1]+1)for b in scan(frame,size,ink))
def propose(frame,ink,controls):
 s=scene(frame)
 if not s:return None
 n=s['size'];pitch=s['pitch'];k=(n-1)//2;start=positions(frame,n,ink)
 if len(start)<2:return None
 background=Counter(v for row in frame[1:]for v in row).most_common(1)[0][0];marks=[p for p in s['cells']if frame[p[0]+k][p[1]+k]==s['mark']]
 allowed=set(start)
 for y in range(start[0][0]%pitch,65-n,pitch):
  for x in range(start[0][1]%pitch,65-n,pitch):
   if y>0 and x>0 and y+n<64 and x+n<64 and all(frame[yy][xx]==background for yy in(y+k,y+k+1)for xx in(x+k,x+k+1)):allowed.add((y,x))
 todo=deque([(start,[])]);seen={start}
 while todo and len(seen)<4096:
  pos,path=todo.popleft()
  for a in marks:
   for d in sorted(controls):
    b=tuple(a[j]+d[j]for j in(0,1));z=tuple(a[j]+2*d[j]for j in(0,1))
    if b in pos and z in pos:return dict(source_scene=s,ink=ink,background=background,start=start,target=pos,path=path,jump=(a,b,z),controls=[dict(delta=d,action=v)for d,v in sorted(controls.items())],hypothesis='test_highlighted_jump_across_and_onto_an_unmodeled_carrier_core')
  for d,a in sorted(controls.items()):
   q=tuple(tuple(p[j]+d[j]for j in(0,1))for p in pos)
   if q not in seen and all(p in allowed for p in q):seen.add(q);todo.append((q,path+[(a,q)]))
 return None
