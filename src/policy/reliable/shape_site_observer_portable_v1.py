from collections import Counter
import math,hashlib,json
from cross_shape_geometry_portable_v1 import scene as old_scene
from endpoint_visible_parts_v1 import parts
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def scene(obs):
 f=obs['frame'];totals=Counter(v for row in f for v in row);bg=totals.most_common(1)[0][0];old,targets=old_scene(obs);objects=[];sites=[]
 for k,o in old.items():objects.append(dict(o,key=k,geometry=o['radius']))
 for q in parts(f):
  if q['color']==bg:continue
  y,x,h,w=q['y'],q['x'],q['h'],q['w']
  if 9<=h<=49 and 9<=w<=49:
   edge={(a,b) for a in range(h) for b in range(w) if a in (0,h-1) or b in (0,w-1)};supported=sum(f[y+a][x+b]==q['color'] for a,b in edge)
   if supported>=.85*len(edge) and q['area']<=1.2*len(edge):
    center=(math.ceil(y+(h-1)/2),math.ceil(x+(w-1)/2));v=f[center[0]][center[1]];objects=[o for o in objects if o['color']!=q['color']];objects.append(dict(color=q['color'],key=str((q['color'],'rectangle')),center=center,geometry=dict(kind='rectangle',radius=((h-1)/2,(w-1)/2)),selected=v not in (bg,q['color']) and totals[v]<=4,boundary_points=[(y+a,x+b) for a,b in sorted(edge)]))
  if 4<=h==w<=12 and 8<q['area']<h*w*.8:sites.append(dict(color=q['color'],box=(y,x,h,w),center=(y+(h-1)/2,x+(w-1)/2),points=[(y+a,x+b) for a,b in q['shape']],source=digest(obs)))
 return objects,targets,sites
