"""Hypothesize a rare token can jump before another action consumes its landing."""
from paired_carrier_geometry_v2 import scene

def proposals(frame):
 s=scene(frame)
 if not s:return []
 n=s['size'];k=(n-1)//2;p=s['pitch'];cells=set(s['cells']);marks=[a for a in cells if frame[a[0]+k][a[1]+k]==s['mark']]
 patterns={tuple((dy,dx)for dy in range(n)for dx in range(n)if frame[a[0]+dy][a[1]+dx]==s['mark'])for a in marks};out=[]
 for a in sorted(cells):
  ink=frame[a[0]+k][a[1]+k]
  if ink in(s['field'],s['mark']):continue
  pattern=tuple((dy,dx)for dy in range(n)for dx in range(n)if frame[a[0]+dy][a[1]+dx]==ink)
  if pattern not in patterns:continue
  for d in [(-p,0),(p,0),(0,-p),(0,p)]:
   b=tuple(a[j]+d[j]for j in(0,1));z=tuple(a[j]+2*d[j]for j in(0,1))
   if b in marks and z in cells and all(frame[z[0]+dy][z[1]+dx]==s['field']for dy in range(n)for dx in range(n)):
    out.append(dict(scene=s,jump=(a,b,z),actor_ink=ink,pattern=pattern,hypothesis='test_distinct_actor_before_the_adjacent_ordinary_mark_is_moved'))
 return out
