"""Fit reflected template groups to all goal pixels, allowing disconnected components."""
from itertools import product
from modal_scene_v14 import objects,shape,marker_ink
from reflection_axes_v4 import axes

def pixels(p):return{(p['y']+y,p['x']+x)for y,x in shape(p)}
def part(points,ink):
 y=min(a for a,b in points);x=min(b for a,b in points);return dict(color=ink,y=y,x=x,h=max(a for a,b in points)-y+1,w=max(b for a,b in points)-x+1,area=len(points),shape=tuple(sorted((a-y,b-x)for a,b in points)))
def infer(o):
 ps=objects(o);f=o['frame']
 for ax in axes(o):
  for ink in sorted({p['color']for p in ps if p['color']!=ax['ink']}):
   bs=[p for p in ps if p['color']==ink and p['h']<24 and p['w']<24]
   if len(bs)<(1 if ax['axis']=='both'else 2)or len(bs)>4:continue
   if not all(any(f[p['y']+y][p['x']+x]!=ink for y,x in shape(p))for p in bs):continue
   for goalink in sorted({p['color']for p in ps if p['color']not in(ink,ax['ink'])}):
    components=[p for p in ps if p['color']==goalink];mask=set().union(*(pixels(p)for p in components))if components else set()
    if not mask:continue
    cy=(min(y for y,x in mask)+max(y for y,x in mask))/2;cx=(min(x for y,x in mask)+max(x for y,x in mask))/2
    center=(cy,cx)if ax['axis']=='both'else cy if ax['axis']=='horizontal'else cx
    current=(ax['center_y'],ax['center_x'])if ax['axis']=='both'else(ax['center'],);desired=(cy,cx)if ax['axis']=='both'else(center,)
    if any((a-b)%1 for a,b in zip(current,desired)):continue
    H=lambda p:(int(2*cy-p[0]),p[1]);V=lambda p:(p[0],int(2*cx-p[1]));HV=lambda p:(int(2*cy-p[0]),int(2*cx-p[1]));I=lambda p:p
    groups=[('double',[I,HV]),('four',[I,H,V,HV])]if ax['axis']=='both'else[('horizontal',[I,H])]if ax['axis']=='horizontal'else[('vertical',[I,V])]
    for group,transforms in groups:
     if any({tr(p)for p in mask}!=mask for tr in transforms):continue
     choices=[]
     for b in bs:
      first=shape(b)[0];candidates=[]
      for y,x in sorted(mask):
       yy,xx=y-first[0],x-first[1];points={(yy+a,xx+c)for a,c in shape(b)}
       if not points<=mask:continue
       images=[{tr(p)for p in points}for tr in transforms];covered=set().union(*images)
       if covered<=mask:candidates.append((abs(yy-b['y'])+abs(xx-b['x']),images,covered))
      choices.append(candidates)
     if not all(choices):continue
     best=None
     for combo in product(*choices):
      if set().union(*(c[2]for c in combo))!=mask:continue
      overlap=sum(len(a[1][0]&b[1][0])for i,a in enumerate(combo)for b in combo[i+1:]);cost=sum(c[0]for c in combo)+1000*overlap
      if best is None or cost<best[0]:best=(cost,combo)
     if best:return dict(axis=ax,target_axis=center,pairs=[dict(body=b,goal=part(c[1][0],goalink),reflected_goal=part(c[1][-1],goalink),images=[part(pts,goalink)for pts in c[1]])for b,c in zip(bs,best[1])],body_ink=ink,goal_ink=goalink,marker=marker_ink(o),goal_components=components,composite_goal_hypothesis=True,reflection_group=group)
 return None
