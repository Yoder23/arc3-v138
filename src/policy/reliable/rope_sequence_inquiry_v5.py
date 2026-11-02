"""Retain the requested sequence; verify collection feedback and retract without ejecting a learned item."""
import copy
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.level=None;self.goal=[];self.collected=[];self.phase='align';self.previous=None;self.last=None;self.effects=[];self.moves={};self.steps=0;self.pending_color=None;self.targets={};self.detour_row=None;self.stagnant=0;self.rails=[];self.rail_memory=[]
 def respond(self,o):
  ps=parts(o['frame']);legends=[p for p in ps if p['y']>=54 and p['h']==p['w']==6 and p['area']==18];head=None;a=None;data={};target=None;reason='unresolved_rope_sequence'
  if self.level!=o['levels_completed']:
   self.level=o['levels_completed'];self.goal=sorted([p for p in ps if p['y']>=54 and p['h']==p['w']==4 and p['area']==16],key=lambda p:p['x']);self.collected=[];self.phase='align';self.steps=0;self.pending_color=None;self.previous=None;self.targets={};self.detour_row=None;self.stagnant=0;self.rail_memory.extend(copy.deepcopy(self.rails));self.rails=[]
   for p in ps:
    if p['h']==p['w']==4 and p['area']==16 and p['y']<50:
     x=p['x']+1;points=[(y,x) for y in range(3,50) if set(o['frame'][y][x:x+2])=={2,3}]
     if len(points)>=8 and max(y for y,x in points)-min(y for y,x in points)>=12 and not any(q['x']==x for q in self.rails):self.rails.append(dict(x=x,bottom=max(y for y,x in points),top=min(y for y,x in points),points=points,source=digest(o)))
  if len(legends)==1:
   heads=[p for p in ps if p['color']==legends[0]['color'] and p['h']==p['w']==6 and p['area']==18 and p['y']<50]
   if len(heads)==1:head=heads[0]
  if self.previous is not None:
   e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(o));src=digest(e);self.effects.append(dict(source=src,progress=o['levels_completed']>self.previous['levels_completed'] or o['state']=='WIN'))
   self.stagnant=self.stagnant+1 if self.previous['frame'][:50]==o['frame'][:50] else 0
   c=self.last['certificate']
   if c and head and self.last['action'] in (1,2):
    old=c['head'];delta=[head['y']-old['y'],head['x']-old['x']]
    if any(delta):self.moves[self.last['action']]=dict(delta=delta,source=src,before=old,after=head)
  visible_goal=sorted([p for p in ps if p['y']>=54 and p['h']==p['w']==4 and p['area']==16],key=lambda p:p['x']);remaining=[p['color'] for p in visible_goal]
  matched=[]
  for p in self.goal:
   if any(q['x']==p['x'] and q['y']==p['y'] and q['color']==p['color'] for q in visible_goal):break
   matched.append(p['color'])
  if len(matched)>len(self.collected):self.collected=matched;self.pending_color=None;self.phase='retract'
  if head and self.goal and o['state']=='NOT_FINISHED' and self.steps<200 and self.stagnant<3:
   if self.collected and self.phase in ('retract','free_from_rail'):
    carried=[p for p in ps if p['h']==p['w']==4 and p['area']==16 and p['color']==self.collected[-1] and p['y']<50];item=carried[0] if len(carried)==1 else None;rail=next((q for q in self.rails if item and item['x']+1==q['x'] and item['y']<=q['bottom']),None)
    if rail:self.phase='free_from_rail';a=2;reason='test_vertical_release_before_horizontal_pull'
    elif self.phase=='free_from_rail':self.phase='retract'
   if self.phase=='retract':
    items=[p for p in ps if p['color'] in self.collected and p['y']==head['y']+1 and p['h']==p['w']==4 and p['area']==16];right=max((p['x'] for p in items),default=head['x']+7);minimum=head['x']+7+6*(len(self.collected)-1)
    if right>minimum:a=3;reason='retract_observed_collected_objects_to_reserved_slots'
    else:self.phase='align'
   if a is None and len(self.collected)<len(self.goal):
    color=self.goal[len(self.collected)]['color'];targets=[p for p in ps if p['color']==color and p['h']==p['w']==4 and p['area']==16 and p['y']<50]
    if len(targets)==1:
     target=targets[0];self.targets[color]=copy.deepcopy(target);desired=target['y']-1
     obstacles=[p for p in ps if p['h']==p['w']==4 and p['area']==16 and p['y']==target['y'] and head['x']<p['x']<target['x'] and p['color'] not in self.collected]
     if self.phase=='align' and obstacles:
      fields=[p for p in ps if p['y']<50 and p['h']>=12 and p['w']>=12 and p['area']>=200];occupied={p['y']-1 for p in ps if p['h']==p['w']==4 and p['area']==16 and p['y']<50 and p['color'] not in self.collected};rows=[y for f in fields for y in range(f['y'],f['y']+f['h']-5) if (y-head['y'])%6==0 and y not in occupied]
      if rows:self.detour_row=min(rows,key=lambda y:(abs(y-(desired+6)),abs(y-head['y']),y));self.phase='detour'
     if self.phase=='detour':
      tip=max((p['x']+x for p in ps if p['color'] in (1,2) and head['y']<=p['y']<head['y']+6 for y,x in p['shape']),default=head['x']+5)
      if head['y']!=self.detour_row:a=1 if self.detour_row<head['y'] else 2;reason='route_around_out_of_order_objects'
      elif tip<target['x']-2:a=4;reason='extend_to_clear_only_out_of_order_objects'
      elif tip>target['x']-2:a=3;reason='retract_to_preserve_requested_object_during_clearance'
      else:self.phase='approach'
     if a is None and self.phase=='approach':
      if head['y']!=desired:a=1 if desired<head['y'] else 2;reason='push_obstructions_to_adjacent_row_before_requested_contact'
      else:a=4;reason='verify_requested_endpoint_contact'
     elif a is None and self.phase=='align' and head['y']!=desired:
      distance=desired-head['y'];options=[a for a,m in self.moves.items() if m['delta'][0]*distance>0];a=options[0] if options else (1 if distance<0 else 2);reason='align_retained_sequence_with_next_object'
     elif a is None:self.phase='extend';self.pending_color=color;a=4;reason='extend_until_observed_collection_feedback'
  c=None
  if a is not None:self.steps+=1;c=dict(kind='rope_sequence_hypothesis',context=digest(o),action=a,head=head,target=target,goal=self.goal,visible_goal=visible_goal,collected=self.collected[:],moves=copy.deepcopy(self.moves),effects=copy.deepcopy(self.effects),goal_is_hypothesis=True,phase=self.phase,rails=copy.deepcopy(self.rails),retained_rail_lessons=len(self.rail_memory))
  r=dict(action=a,data=data,done=a is None,certificate=c,advisor='rope_sequence',diagnostics=dict(reason=reason,steps=self.steps,phase=self.phase,collected=self.collected[:]));self.previous=copy.deepcopy(o);self.last=copy.deepcopy(r);return r
