from collections import Counter
from shape_site_observer_portable_v1 import scene as prior_scene,digest
from cross_color_surface_portable_v1 import sites
from rectangle_contact_model_v2 import points
from elastic_figure_model_v1 import fit_rect

def partial_pads(o,pads):
 f=o['frame'];out=list(pads)
 for y in range(0,60):
  for x in (-2,-1,62,63):
   body={(a,b) for a in range(y,y+3) for b in range(x,x+3) if 0<=b<64};ring={(a,b) for a in range(y-1,y+4) for b in range(x-1,x+4) if a in (y-1,y+3) or b in (x-1,x+3)};ring={(a,b) for a,b in ring if 0<=a<62 and 0<=b<64};colors={f[a][b] for a,b in body}
   if len(colors)==1 and next(iter(colors)) not in (2,5) and ring and all(f[a][b]==2 for a,b in ring):
    p=dict(color=next(iter(colors)),y=y,x=x,size=3)
    if p not in out:out.append(p)
 return out

def scene(o):
 objects,targets,_=prior_scene(o);f=o['frame'];figures=[]
 if not objects or any(q['geometry']['kind']!='rectangle' for q in objects):return None
 for q in objects:
  ps=q['boundary_points'];a=min(y for y,x in ps);b=min(x for y,x in ps);c=max(y for y,x in ps);d=max(x for y,x in ps)
  figures.append(dict(kind='elastic_rectangle',color=q['color'],state=[a,b,c,d],perimeter=c-a+d-b,selected=q['selected']))
 if len(figures)!=len(targets) or len(figures)<2:return None
 bg=Counter(v for row in f for v in row).most_common(1)[0][0];pads=partial_pads(o,sites(o));blue=[(y,x) for y,row in enumerate(f[:62]) for x,c in enumerate(row) if c==1]
 sc=dict(figures=sorted(figures,key=lambda q:q['color']),targets=targets,paints=pads,site=dict(color=1,points=blue),background=bg,initial_source=digest(o))
 if not all(fit_rect(q['state'],q['color'],f,sc,[v['color'] for v in figures if v is not q]) for q in figures):return None
 return sc
