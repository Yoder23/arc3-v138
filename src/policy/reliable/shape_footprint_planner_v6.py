"""Retain observed deformations, route whole figures, and test alternatives when goals do not fit."""
import copy
from collections import deque
from shape_site_inquiry_v3 import Agent as Inquiry,scene
from visible_components_v1 import parts
from visual_transform_learner import digest

def body(obs,color):
 return sorted({(q['y']+a,q['x']+b) for q in parts(obs['frame']) if q['color']==color and q['area']>=3 for a,b in q['shape']})
class Agent:
 def __init__(self):self.prior=Inquiry();self.previous=None;self.last=None;self.observations={};self.events={};self.planning=False;self.level=None;self.targets={};self.goal_source=None;self.placed=set();self.footprints={};self.layouts={};self.steps=0;self.sequence=None;self.probed=set();self.probe_color=None;self.geometry_changes=[];self.recovery=None
 def respond(self,obs):
  if not self.planning:
   r=self.prior.respond(obs)
   if self.prior.site and self.prior.site['source']==digest(obs):self.observations[digest(obs)]=copy.deepcopy(obs)
   if not r['done'] or obs['state']!='NOT_FINISHED':return self.finish(obs,r)
   if not self.prior.site:return self.finish(obs,r)
   self.planning=True;self.level=obs['levels_completed'];self.goal_source=self.prior.site['source'];self.targets=scene(self.observations[self.goal_source])[1]
  objects,_,_=scene(obs);active=next((o for o in objects if o['selected']),None);models={a:m for a,m in self.prior.models.items() if len({tuple(q['origin']) for q in m['support']})>=2};action=None;reason='unresolved_footprint';goal=None;path=None;proof=None
  selection_hypothesis=None
  if active is None and self.last and self.last['action'] in (1,2,3,4):
   old=(self.last.get('certificate') or {}).get('object');matches=[o for o in objects if old and o['color']==old['color']]
   if len(matches)==1:
    active=copy.deepcopy(matches[0]);active['selected']=True;event=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));selection_hypothesis=dict(source=digest(event),previous_object=old,interpretation='retained_selection_under_badge_occlusion')
  if self.recovery or (active is None and self.last and self.last['action'] in models):
   old=(self.last.get('certificate') or {}).get('object');rects=[o for o in objects if o['geometry']['kind']=='rectangle']
   if self.recovery is None and old and rects and old['color']!=rects[0]['color']:self.recovery=dict(stage='select',blocked=old['color'],blocker=rects[0]['color'],source=digest(obs))
   if self.recovery:
    obj=next((o for o in objects if o['color']==self.recovery['blocker']),None);probe=None
    if self.recovery['stage']=='select':
     if obj and obj['selected']:self.recovery['stage']='move'
     else:probe=5
    if self.recovery['stage']=='move' and obj:
     points=body(obs,obj['color']);legal=[(m['delta'][0],a) for a,m in models.items() if all(0<=y+m['delta'][0]<62 and 0<=x+m['delta'][1]<64 for y,x in points)]
     if legal:probe=max(legal)[1];self.recovery['stage']='restore';self.placed.discard(obj['color'])
    elif self.recovery['stage']=='restore':probe=5;self.recovery=None
    if probe is not None and obj:
     self.steps+=1;cert=dict(kind='shape_site_inquiry',context=digest(obs),action=probe,object=obj,site=self.prior.site,models=models,target=None,retreating=False,interaction_is_hypothesis=True,outcomes=[],visibility_probe=True)
     return self.finish(obs,dict(action=probe,data={},done=False,certificate=cert,advisor='shape_footprint_planner',diagnostics=dict(reason='move_occluding_figure_to_reveal_active_geometry',steps=self.steps)))
  if active and obs['state']=='NOT_FINISHED' and obs['levels_completed']==self.level and self.steps<128:
   color=active['color'];center=tuple(active['center']);points=body(obs,color);offsets=tuple(sorted((y-center[0],x-center[1]) for y,x in points));old=self.footprints.get(color)
   if old and self.probe_color==color and self.sequence is None and color not in self.probed:
    difference=set(offsets)^set(map(tuple,old['offsets']))
    expected_pixels={(center[0]+a,center[1]+b) for a,b in old['offsets']};contact_expected=bool(expected_pixels&set(map(tuple,self.prior.site['points'])))
    if len(difference)>=6 and contact_expected and self.last and self.last['action'] in models:
     before_color=self.last.get('certificate',{}).get('object',{}).get('color')
     if before_color==color:
      event=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));self.geometry_changes.append(dict(source=digest(event),before_footprint=old,after_points=points,after_center=center));delta=models[self.last['action']]['delta'];reverse=next((a for a,m in models.items() if tuple(m['delta'])==tuple(-v for v in delta)),None)
      if reverse is not None:self.sequence=[self.last['action']]*2+[reverse]*2;self.probed.add(color)
   if self.sequence is not None:
    if self.sequence:action=self.sequence.pop(0);reason='repeat_and_retreat_after_new_geometry'
    else:self.sequence=None;self.footprints.pop(color,None);self.layouts.pop(color,None);self.probe_color=None
   if action is None:
    if color not in self.footprints:self.footprints[color]=dict(source=digest(obs),color=color,center=center,points=points,offsets=offsets)
    proof=self.footprints[color];offsets=set(map(tuple,proof['offsets']))
    # A selected center pixel is UI. Coverage below uses observed body pixels only.
    if color not in self.layouts:
     targets=set(map(tuple,self.targets.get(color,[])));choices=[];sy=min(abs(m['delta'][0]) for m in models.values() if m['delta'][0]);sx=min(abs(m['delta'][1]) for m in models.values() if m['delta'][1])
     for y in range(center[0]%sy,62,sy):
      for x in range(center[1]%sx,64,sx):
       translated={(y+a,x+b) for a,b in offsets}
       if targets and targets<=translated and all(0<=a<62 and 0<=b<64 for a,b in translated):choices.append((abs(y-center[0])+abs(x-center[1]),(y,x)))
     if choices:self.layouts[color]=min(choices)[1]
    goal=self.layouts.get(color)
    if goal and center==tuple(goal):self.placed.add(color)
    if color in self.placed:
     if set(self.targets)-self.placed and 5 in obs['available_actions']:action=5;reason='select_next_unplaced_figure'
     else:reason='placed_hypotheses_without_progress'
    elif goal:
     queue=deque([(center,[])]);seen={center};site=set(map(tuple,self.prior.site['points']))
     while queue:
      at,seq=queue.popleft()
      if at==tuple(goal):path=seq;break
      for a,m in sorted(models.items()):
       nxt=tuple(at[i]+m['delta'][i] for i in (0,1));pixels={(nxt[0]+y,nxt[1]+x) for y,x in offsets}
       if nxt not in seen and pixels and all(0<=y<62 and 0<=x<64 for y,x in pixels) and not pixels&site:seen.add(nxt);queue.append((nxt,seq+[a]))
     if path:action=path[0];reason='route_retained_figure_around_interaction_site'
    elif color not in self.probed:
     self.probe_color=color;target=self.prior.site['center'];options=[(sum(abs(center[i]+m['delta'][i]-target[i]) for i in (0,1)),a) for a,m in models.items() if all(0<=center[i]+m['delta'][i]<62+(2 if i==1 else 0) for i in (0,1))]
     if options:action=min(options)[1];reason='test_site_when_current_figure_cannot_cover_goals'
  cert=None
  if action is not None:
   self.steps+=1;cert=dict(kind='shape_site_inquiry',context=digest(obs),action=action,object=active,site=self.prior.site,models=models,target=goal,retreating=False,interaction_is_hypothesis=True,outcomes=[],footprint=proof,goal_source=self.goal_source,goal_targets=self.targets.get(active['color'],[]),route=path,geometry_changes=copy.deepcopy(self.geometry_changes),selection_hypothesis=selection_hypothesis)
  r=dict(action=action,data={},done=action is None,certificate=cert,advisor='shape_footprint_planner',diagnostics=dict(reason=reason,steps=self.steps,objects=objects,placed=sorted(self.placed),geometry_changes=copy.deepcopy(self.geometry_changes),selection_hypothesis=selection_hypothesis))
  return self.finish(obs,r)
 def finish(self,obs,r):self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r);return r
