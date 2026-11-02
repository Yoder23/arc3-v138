"""Bounded contact-retreat inquiry for a novel hollow interaction site."""
import copy,math
from collections import Counter
from cross_alignment_learner_v20 import Agent as Prior
from cross_shape_geometry_v2 import scene as old_scene
from visible_components_v1 import parts
from visual_transform_learner import digest

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
class Agent:
 def __init__(self):self.prior=Prior();self.exploring=False;self.previous=None;self.last=None;self.site=None;self.target=None;self.origin=None;self.color=None;self.models={};self.steps=0;self.retreating=False;self.outcomes=[];self.level=None;self.tested_level=None;self.sequence=None
 def respond(self,obs):
  if not self.exploring:
   if self.tested_level==obs['levels_completed']:return self.prior.respond(obs)
   self.tested_level=obs['levels_completed'];objs,targets,sites=scene(obs)
   if not sites or not any(o['geometry']['kind']=='rectangle' for o in objs):return self.prior.respond(obs)
   self.prior.respond(obs);source=self.prior.shared if self.prior.shared else self.prior.prior;self.models=copy.deepcopy(source.models);self.exploring=True;self.level=obs['levels_completed'];self.site=sites[0]
  objs,targets,sites=scene(obs)
  if self.previous is not None:
   event=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));self.outcomes.append(dict(source=digest(event),before=scene(self.previous)[0],after=objs,progress=obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN'))
  active=next((o for o in objs if o['selected']),None);action=None;cert=None;reason='bounded_shape_site_inquiry_stopped'
  models={a:m for a,m in self.models.items() if len({tuple(p['origin']) for p in m['support']})>=2}
  if self.sequence is None and self.last and active:
   old=self.last['certificate']['object']
   if old['color']==active['color'] and old['geometry']!=active['geometry'] and self.last['action'] in models:
    delta=models[self.last['action']]['delta'];opposite=next((a for a,m in models.items() if tuple(m['delta'])==tuple(-v for v in delta)),None)
    if opposite is not None:self.sequence=[self.last['action']]*2+[opposite]*2
  if self.sequence is not None:
   if self.sequence and active:
    action=self.sequence.pop(0);self.steps+=1;cert=dict(kind='shape_site_inquiry',context=digest(obs),action=action,object=active,site=self.site,models=models,target=self.origin,retreating=len(self.sequence)<2,interaction_is_hypothesis=True,outcomes=copy.deepcopy(self.outcomes));reason='repeat_then_retreat_from_observed_deformation'
   else:reason='completed_deformation_retreat_probe'
   response=dict(action=action,data={},done=action is None,certificate=cert,advisor='shape_site_inquiry',diagnostics=dict(reason=reason,steps=self.steps,objects=objs,outcomes=copy.deepcopy(self.outcomes)))
   self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(response);return response
  if self.steps<40 and obs['state']=='NOT_FINISHED' and obs['levels_completed']==self.level and active:
   if self.color is None:self.color=active['color'];self.origin=tuple(active['center'])
   if active['color']==self.color:
    if self.target is None:
     sy=min(abs(m['delta'][0]) for m in models.values() if m['delta'][0]);sx=min(abs(m['delta'][1]) for m in models.values() if m['delta'][1]);cy,cx=active['center'];self.target=min(((y,x) for y in range(cy%sy,62,sy) for x in range(cx%sx,64,sx)),key=lambda p:sum(abs(p[i]-self.site['center'][i]) for i in (0,1)))
    if tuple(active['center'])==self.target:
     if not self.retreating:self.target=self.origin;self.retreating=True
     else:self.target=None;reason='completed_contact_retreat'
    if self.target is not None:
     c=active['center'];options=[(sum(abs(c[i]+m['delta'][i]-self.target[i]) for i in (0,1)),a) for a,m in models.items() if all(0<=c[i]+m['delta'][i]<62+(2 if i==1 else 0) for i in (0,1))]
     if options:action=min(options)[1];reason='retreat_after_contact' if self.retreating else 'test_hollow_site_contact'
   else:action=5;reason='restore_inquiry_object_selection'
   if action is not None:self.steps+=1;cert=dict(kind='shape_site_inquiry',context=digest(obs),action=action,object=active,site=self.site,models=models,target=self.target,retreating=self.retreating,interaction_is_hypothesis=True,outcomes=copy.deepcopy(self.outcomes))
  response=dict(action=action,data={},done=action is None,certificate=cert,advisor='shape_site_inquiry',diagnostics=dict(reason=reason,steps=self.steps,objects=objs,outcomes=copy.deepcopy(self.outcomes)))
  self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(response);return response
