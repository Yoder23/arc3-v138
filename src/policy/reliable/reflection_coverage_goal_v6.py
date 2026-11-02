"""Rank bounded reflected-layout hypotheses by pixel agreement; no completion claim."""
from itertools import product
from modal_scene_v14 import objects,shape,marker_ink
from modal_scene_v12 import objects as fine_objects
from reflection_goal_assignment_v13 import part,pixels
from reflection_axes_v4 import axes

def bitmap(points):
 result=0
 for y,x in points:
  if 0<=y<64 and 0<=x<64:result|=1<<(y*64+x)
 return result

def candidates(o,limit=12):
 ps=objects(o);f=o['frame'];out=[]
 for ax in axes(o):
  if ax['axis']!='both':continue
  for ink in sorted({p['color']for p in ps if p['color']!=ax['ink']}):
   bs=[p for p in ps if p['color']==ink and p['h']<24 and p['w']<24]
   if len(bs)!=2 or not all(any(f[p['y']+y][p['x']+x]!=ink for y,x in shape(p))for p in bs):continue
   for goalink in sorted({p['color']for p in fine_objects(o)if p['color']not in(ink,ax['ink'])}):
    components=[p for p in fine_objects(o)if p['color']==goalink];mask=set().union(*(pixels(p)for p in components))if components else set()
    if len(mask)<24:continue
    cy=(min(y for y,x in mask)+max(y for y,x in mask))/2;cx=(min(x for y,x in mask)+max(x for y,x in mask))/2;target=bitmap(mask)
    if any((a-b)%1 for a,b in zip((ax['center_y'],ax['center_x']),(cy,cx))):continue
    I=lambda p:p;H=lambda p:(int(2*cy-p[0]),p[1]);V=lambda p:(p[0],int(2*cx-p[1]));HV=lambda p:(int(2*cy-p[0]),int(2*cx-p[1]))
    for group,tr in(('four',[I,H,V,HV]),):
     for combine in('union',):
      lists=[]
      for b in bs:
       rows=[]
       from math import gcd
       step=0
       for yy in range(b['h']):
        xs=sorted(x for y,x in shape(b)if y==yy);run=0;last=None
        for xx in xs:
         if last is not None and xx!=last+1:step=gcd(step,run);run=0
         run+=1;last=xx
        if run:step=gcd(step,run)
       step=max(1,step)
       for y in range(b['y']%step,65-b['h'],step):
        for x in range(b['x']%step,65-b['w'],step):
         points={(y+a,x+c)for a,c in shape(b)};images=[{fn(p)for p in points}for fn in tr]
         if any(not(0<=yy<64 and 0<=xx<64)for pp in images for yy,xx in pp):continue
         code=0
         for pp in images:code=(code|bitmap(pp))if combine=='union'else(code^bitmap(pp))
         rows.append((code,part(points,goalink),images,abs(y-b['y'])+abs(x-b['x'])))
       lists.append(rows)
      scored=[]
      for a,b in product(*lists):
       code=(a[0]|b[0])if combine=='union'else(a[0]^b[0]);error=(code^target).bit_count();overlap=len(pixels(a[1])&pixels(b[1]));cost=((target&~code).bit_count(),(code&~target).bit_count(),overlap,a[3]+b[3]);scored.append((cost,a,b,code))
      scored.sort(key=lambda q:q[0])
      for cost,a,b,code in scored[:limit]:out.append(dict(cost=cost,group=group,composition=combine,axis=ax,target_axis=(cy,cx),body_ink=ink,goal_ink=goalink,marker=marker_ink(o),goal_components=components,pairs=[dict(body=body,goal=q[1],images=[part(pp,goalink)for pp in q[2]])for body,q in zip(bs,(a,b))],prediction_pixels=code.bit_count(),observed_pixels=len(mask),mismatched_pixels=cost[0]+cost[1],uncovered_pixels=cost[0],extra_pixels=cost[1],approximate_hypothesis=True))
 out.sort(key=lambda q:q['cost']);return out[:limit]

def infer(o):
 from reflection_goal_assignment_v13 import infer as exact
 a=exact(o)
 if a:return a
 for q in candidates(o):
  if q['uncovered_pixels']:continue
  return dict(axis=q['axis'],target_axis=q['target_axis'],pairs=[dict(body=p['body'],goal=p['goal'],reflected_goal=p['images'][-1],images=p['images'])for p in q['pairs']],body_ink=q['body_ink'],goal_ink=q['goal_ink'],marker=q['marker'],goal_components=q['goal_components'],composite_goal_hypothesis=True,reflection_group=q['group'],coverage_hypothesis=True,extra_pixels=q['extra_pixels'])
 return None
