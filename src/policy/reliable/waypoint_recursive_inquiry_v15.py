"""Probe recursive combination of visible blocks when a single-actor model fails."""
import copy
from collections import Counter
from waypoint_scene_inquiry_v3 import Agent as Prior
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.prior=Prior();self.tried={};self.steps=0;self.previous=None;self.last=None;self.effects=[];self.level=None;self.moving={};self.motion_events=[]
 def respond(self,obs):
  if self.level!=obs['levels_completed']:self.level=obs['levels_completed'];self.steps=0;self.moving={};self.motion_events=[]
  if self.previous is not None:
   event=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));changed=sum(a!=b for r,s in zip(self.previous['frame'][8:62],obs['frame'][8:62]) for a,b in zip(r,s));self.effects.append(dict(source=digest(event),changed_board_pixels=changed,progress=obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN'))
  r=self.prior.respond(obs)
  if not r['done'] or obs['state']!='NOT_FINISHED':self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r);self.prior.prior.last=copy.deepcopy(r);return r
  ps=parts(obs['frame']);blocks=[p for p in ps if p['y']>=8 and p['h']==p['w'] and p['area']==p['h']*p['w'] and 1<=p['h']<=5];regions=[p for p in ps if p['y']>=8 and p['h']==p['w'] and 7<=p['h']<=12 and p['area']>=.5*p['h']*p['w']];key=digest(dict(level=obs['levels_completed'],blocks=[{k:p[k] for k in ['color','y','x','h','w']} for p in blocks]));tried=self.tried.setdefault(key,set());candidates=[]
  palette={p['color'] for p in ps if p['y']<3 and p['h']==p['w']==2 and p['area']==4}
  if palette:blocks=[p for p in blocks if p['color'] in palette]
  key=digest(dict(level=obs['levels_completed'],blocks=[{k:p[k] for k in ['color','y','x','h','w']} for p in blocks]));tried=self.tried.setdefault(key,set())
  compact=lambda p:{k:p[k] for k in ('color','y','x','h','w','area')}
  snapshot=dict(palette=sorted(palette),tokens=[compact(p) for p in blocks],goals=[compact(p) for p in regions],requests=[compact(p) for p in ps if 3<=p['y']<8 and p['h']==p['w'] and p['area']==p['h']*p['w'] and p['h']<=5])
  requested=Counter((p['color'],p['h']) for p in ps if 3<=p['y']<8 and p['h']==p['w'] and p['area']==p['h']*p['w'] and p['h']<=5);placed_blocks=[];placed_regions=[]
  for p in sorted(blocks,key=lambda p:-p['h']):
   kind=(p['color'],p['h']);point=(p['y']+p['h']//2,p['x']+p['w']//2)
   matched=next((g for g in regions if g not in placed_regions and max(abs(point[i]-(g['y']+g['h']//2,g['x']+g['w']//2)[i]) for i in (0,1))<=1),None)
   if matched is not None and requested[kind]>0:placed_blocks.append(p);placed_regions.append(matched);requested[kind]-=1
  snapshot['reserved_tokens']=[compact(p) for p in placed_blocks];snapshot['reserved_goals']=[compact(p) for p in placed_regions]
  blocks=[p for p in blocks if p not in placed_blocks];regions=[g for g in regions if g not in placed_regions]
  reach=max([max(abs(v) for v in q['delta']) for q in self.prior.prior.motion] or [3])
  for p in blocks:
   point=(p['y']+p['h']//2,p['x']+p['w']//2);distance=min((abs(point[0]-g['y']-g['h']//2)+abs(point[1]-g['x']-g['w']//2) for g in regions),default=0);
   if any(q is not p and q['color']==p['color'] and max(abs(point[i]-(q['y']+q['h']//2,q['x']+q['w']//2)[i]) for i in (0,1))<=reach*1.5 for q in blocks):candidates.append((-p['h'],distance,point,'test_visible_block_combination'))
  reach=max([max(abs(v) for v in q['delta']) for q in self.prior.prior.motion] or [3])
  requested_colors={color for (color,size),number in requested.items() if number>0}
  for p in blocks:
   origin=(p['y']+p['h']//2,p['x']+p['w']//2);others=[q for q in blocks if q is not p and q['color']==p['color'] and q['h']==p['h']]
   targets=[(q['y']+q['h']//2,q['x']+q['w']//2) for q in others]
   if not targets and (len(blocks)==1 or p['color'] in requested_colors):targets=[(q['y']+q['h']//2,q['x']+q['w']//2) for q in regions]
   for target in targets:
    point=tuple(origin[i]+max(-reach,min(reach,target[i]-origin[i])) for i in (0,1));distance=max(abs(target[i]-point[i]) for i in (0,1))
    if point!=origin:candidates.append((-p['h']-1,distance,point,'test_short_move_toward_matching_block_or_goal'))
  for g in regions:candidates.append((0,0,(g['y']+g['h']//2,g['x']+g['w']//2),'test_goal_region_after_combination'))
  # Track unassigned small sprites by actual color-pixel translation, excluding the token legend.
  hazards=[]
  if self.previous is not None and self.previous['levels_completed']==obs['levels_completed']:
   def clouds(frame):
    out={}
    for y,row in enumerate(frame[8:62],8):
     for x,c in enumerate(row):
      if c not in palette:out.setdefault(c,[]).append((y,x))
    return {c:v for c,v in out.items() if 3<=len(v)<=32}
   def split(points):
    rest=set(points);groups=[]
    while rest:
     seed=rest.pop();group={seed};todo=[seed]
     while todo:
      a=todo.pop();near={b for b in rest if max(abs(a[i]-b[i]) for i in (0,1))<=2};rest-=near;group|=near;todo+=list(near)
     if len(group)>=3:groups.append(sorted(group))
    return groups
   def center(points):return tuple((min(p[i] for p in points)+max(p[i] for p in points))/2 for i in (0,1))
   old,new=clouds(self.previous['frame']),clouds(obs['frame'])
   for color,points in new.items():
    if color not in old:continue
    aa,bb=split(old[color]),split(points);used=set();current=[]
    for group in bb:
     b=center(group);matches=sorted((max(abs(b[j]-center(g)[j]) for j in (0,1)),i) for i,g in enumerate(aa) if i not in used and len(g)==len(group))
     if not matches or matches[0][0]>16:continue
     _,ix=matches[0];used.add(ix);a=center(aa[ix]);delta=tuple(b[i]-a[i] for i in (0,1))
     if any(delta):
      proof=dict(source=self.effects[-1]['source'],color=color,before_center=a,after_center=b,delta=delta,before_points=aa[ix],after_points=group);self.moving.setdefault(color,[]).append(proof)
     current.append((b,group))
    if len(self.moving.get(color,[]))>=2:
     for b,group in current:hazards.append(dict(color=color,center=b,points=group,evidence=self.moving[color][-6:]))
  for p in blocks:
   origin=(p['y']+p['h']//2,p['x']+p['w']//2)
   if p['h']==1:continue
   for h in hazards:
    dist=max(abs(origin[i]-h['center'][i]) for i in (0,1));speed=max(max(abs(v) for v in e['delta']) for e in h['evidence'][-2:]);margin=max(10,min(14,speed*3))
    if dist>margin:continue
    for q in blocks:
     if q is p or q['h']!=p['h'] or q['color']!=p['color']:continue
     other=(q['y']+q['h']//2,q['x']+q['w']//2);point=tuple((origin[i]+other[i])//2 for i in (0,1))
     if max(abs(origin[i]-other[i]) for i in (0,1))<=2*reach:candidates.append((-101,dist,point,'test_defensive_merge_of_threatened_matching_blocks'))
    targets=[(q['y']+q['h']//2,q['x']+q['w']//2) for q in blocks if q is not p and q['h']==p['h'] and q['color']==p['color']]+[(g['y']+g['h']//2,g['x']+g['w']//2) for g in regions]
    escapes=[]
    for dy in (-reach,0,reach):
     for dx in (-reach,0,reach):
      point=(origin[0]+dy,origin[1]+dx)
      if point==origin or not (10<=point[0]<=60 and 2<=point[1]<=61):continue
      if any(q is not p and max(abs(point[i]-(q['y']+q['h']//2,q['x']+q['w']//2)[i]) for i in (0,1))<max(abs(point[i]-origin[i]) for i in (0,1)) for q in blocks):continue
      safe=min(max(abs(point[i]-hh['center'][i]) for i in (0,1)) for hh in hazards)
      if safe<=dist:continue
      target_distance=min((max(abs(point[i]-t[i]) for i in (0,1)) for t in targets),default=0)
      crowd=min((max(abs(point[i]-(q['y']+q['h']//2,q['x']+q['w']//2)[i]) for i in (0,1)) for q in blocks if q is not p and q['h']!=p['h']),default=30)
      escapes.append((max(0,16-crowd),target_distance,-safe,point))
    if escapes:
     _,_,_,point=min(escapes);candidates.append((-100,dist,point,'protect_inactive_block_from_observed_moving_sprite'))
  options=[q for q in sorted(candidates) if q[2] not in tried];action=None;data={};cert=None;reason='bounded_recursive_inquiry_stopped'
  if options and self.steps<96:
   _,_,point,reason=options[0];tried.add(point);action=6;data=dict(y=point[0],x=point[1]);self.steps+=1;cert=dict(kind='recursive_block_probe',context=digest(obs),action=6,click=point,pixel=obs['frame'][point[0]][point[1]],goal_is_hypothesis=True,retained_reach_evidence=copy.deepcopy(self.prior.prior.motion),effects=copy.deepcopy(self.effects),moving_sprite_evidence=copy.deepcopy(hazards),scene_evidence=snapshot,reach=reach)
  r=dict(action=action,data=data,done=action is None,certificate=cert,advisor='waypoint_recursive_inquiry',diagnostics=dict(reason=reason,probes=self.steps,retained_effects=len(self.effects)));self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r);self.prior.prior.last=copy.deepcopy(r);return r
