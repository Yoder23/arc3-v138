"""Recover line assemblies from fragmented visible boundaries and color-matched goal markers."""
from collections import Counter
from shape_site_observer_portable_v1 import scene as prior_scene
from cross_color_surface_portable_v1 import sites as paints

def scene(o):
 f=o['frame'];objs,targets,sites=prior_scene(o);pads=paints(o);bg=Counter(v for row in f for v in row).most_common(1)[0][0];mask={(y,x) for p in pads for y in range(p['y']-1,p['y']+p['size']+1) for x in range(p['x']-1,p['x']+p['size']+1)};targetcells={tuple(p) for ps in targets.values() for p in ps};figs=[]
 for q in objs:
  if q['geometry']['kind']!='plus':continue
  y,x=q['center'];ry,rx=q['geometry']['radius'];figs.append(dict(color=q['color'],kind='plus',segments=[dict(axis=0,half=rx),dict(axis=1,half=ry)],state=[y,x,y,x],selected=q['selected']))
 for color in sorted(set(v for row in f[:62] for v in row)-{bg}-set(q['color'] for q in figs)):
  ps={(y,x) for y,row in enumerate(f[:62]) for x,c in enumerate(row) if c==color and (y,x) not in mask|targetcells}
  if len(ps)<28:continue
  yy=[p[0] for p in ps];xx=[p[1] for p in ps];a,c=min(yy),max(yy);b,d=min(xx),max(xx);h=c-a+1;w=d-b+1
  if not(9<=h<=49 and 9<=w<=49) or (a+c)%2 or (b+d)%2:continue
  edge={(y,x) for y in range(a,c+1) for x in range(b,d+1) if y in (a,c) or x in (b,d)}
  if len(ps&edge)<.8*len(edge) or len(ps-edge)>2:continue
  cy,cx=(a+c)//2,(b+d)//2;figs.append(dict(color=color,kind='rectangle',segments=[dict(axis=0,half=(w-1)//2),dict(axis=0,half=(w-1)//2),dict(axis=1,half=(h-1)//2),dict(axis=1,half=(h-1)//2)],state=[a,cx,c,cx,cy,b,cy,d],selected=f[cy][cx]==0))
 centers=[p for p in sites if p['box'][2]>=6]
 if len(figs)!=3 or sum(p['kind']=='rectangle' for p in figs)!=1 or len(targets)!=3 or len(centers)!=1 or len(pads)<3:return None
 return dict(figures=sorted(figs,key=lambda q:q['color']),targets=targets,site=centers[0],paints=pads,background=bg,initial_source=centers[0]['source'])
