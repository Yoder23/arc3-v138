"""Learn movement and switch-induced terrain patches, then plan over joint position and terrain."""
import copy
from collections import deque
from visible_components_v1 import parts
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.level=None;self.field=None;self.actor=None;self.goal=None;self.markers=[];self.buttons=[];self.moves={};self.models={};self.attempts={};self.previous=None;self.last=None;self.pending=None;self.effects=[];self.steps=0;self.knowledge=[];self.explored_pivots=set();self.pivot_move_tests=set();self.active_waypoint=None;self.waypoint_stalls=0
 def find(self,o):
  ps=parts(o['frame']);fields=[p for p in ps if p['x']==0 and 20<=p['w']<48 and 20<=p['h']<60]
  if len(fields)!=1:return
  p=fields[0];self.field={k:p[k] for k in ['x','y','w','h','color']};colors={v for row in o['frame'][p['y']:p['y']+p['h']] for v in row[:p['w']]};self.markers=[q for q in ps if q['h']==q['w']==2 and q['area']==4 and q['x']<p['w'] and p['y']<=q['y']<p['y']+p['h']];self.buttons=[q for q in ps if q['x']>=p['w'] and q['color'] in colors and q['area']>=20 and q['area']>.6*q['h']*q['w']]
  tiles=[q for q in ps if q['x']<p['w'] and q['y']>=p['y'] and q['h']==q['w']==4 and q['area']==16];counts={c:sum(q['color']==c for q in tiles) for c in colors};platform=max(counts,key=counts.get)
  self.buttons += [q for q in tiles if q['color']!=platform]
  self.buttons += [q for q in ps if q['x']<p['w'] and q['y']>=p['y'] and q['color']!=platform and q['area']==q['h']*q['w'] and ((q['h']==4 and q['w']>4) or (q['w']==4 and q['h']>4)) and q not in self.buttons]
  self.buttons += [q for q in ps if q['x']<p['w'] and p['y']<=q['y'] and q['y']+q['h']<=p['y']+p['h'] and q['color'] not in (platform,p['color']) and 4<=q['area']<=8 and sorted((q['h'],q['w']))==[2,4] and q not in self.buttons]
  for q in self.buttons:q['control_id']=str(q['y']+q['h']//2)+','+str(q['x']+q['w']//2)
  self.view=dict(self.field,w=64)
 def positions(self,o):return {p['color']:p for p in parts(o['frame']) if p['h']==p['w']==2 and p['area']==4 and self.field and p['x']<self.field['w'] and self.field['y']<=p['y']<self.field['y']+self.field['h']}
 def path(self,o,actor,target=None):
  target=self.goal if target is None else target
  f=self.view;h,w=f['h'],f['w'];base=[v for row in o['frame'][f['y']:f['y']+h] for v in row[:w]];occluded={(actor['y']+dy-f['y'])*w+actor['x']+dx for dy in (0,1) for dx in (0,1)}
  for m in self.models.values():
   for side in ['before','after']:
    if all(q['i'] in occluded or base[q['i']]==q[side] for q in m['patch']):
     for q in m['patch']:
      if q['i'] in occluded:base[q['i']]=q[side]
     break
  base=tuple(base);variants=[base];index={base:0};links={}
  for k,v in enumerate(variants):
   if len(variants)>32:return None
   for color,m in sorted(self.models.items()):
    for reverse in [False,True]:
     patch=m['patch'];old='after' if reverse else 'before';new='before' if reverse else 'after'
     if all(v[q['i']]==q[old] for q in patch) and all(v[q['i']]==q[old] for q in m.get('guards',[])):
      nxt=list(v)
      for q in patch:nxt[q['i']]=q[new]
      nxt=tuple(nxt)
      if nxt not in index:index[nxt]=len(variants);variants.append(nxt)
      links[(k,color)]=index[nxt]
  def valid(y,x,k):return f['y']<=y and x>=0 and y+2<=f['y']+h and x+2<=self.field['w'] and all(variants[k][(y+dy-f['y'])*w+x+dx]!=f['color'] for dy in (0,1) for dx in (0,1))
  start=(actor['y'],actor['x'],0);queue=deque([(start,[])]);seen={start}
  while queue:
   (y,x,k),path=queue.popleft()
   if [y,x]==[target['y'],target['x']]:return path
   for action,m in sorted(self.moves.items()):
    yy,xx=y+m['delta'][0],x+m['delta'][1];node=(yy,xx,k)
    if node not in seen and valid(yy,xx,k):seen.add(node);queue.append((node,path+[(action,None)]))
   for color in sorted(self.models):
    kk=links.get((k,color));node=(y,x,kk)
    if kk is not None and node not in seen and valid(y,x,kk):seen.add(node);queue.append((node,path+[(6,color)]))
  return None
 def respond(self,o):
  if self.level!=o['levels_completed']:
   self.knowledge.append(dict(field=copy.deepcopy(self.field),moves=copy.deepcopy(self.moves),switches=copy.deepcopy(self.models)));self.level=o['levels_completed'];self.field=None;self.actor=None;self.goal=None;self.moves={};self.models={};self.attempts={};self.previous=None;self.pending=None;self.steps=0;self.explored_pivots=set();self.pivot_move_tests=set();self.active_waypoint=None;self.waypoint_stalls=0;self.find(o)
  if not self.field:return dict(action=None,data={},done=True,certificate=None,advisor='switch_bridge',diagnostics=dict(reason='no_bounded_field'))
  self.find(o)
  positions=self.positions(o)
  if self.previous is not None:
   e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(o));source=digest(e);self.effects.append(dict(source=source,progress=o['levels_completed']>self.previous['levels_completed'] or o['state']=='WIN'))
   if self.last['action'] in (1,2,3,4):
    old=self.positions(self.previous);moved=[(p,positions[color]) for color,p in old.items() if color in positions and (p['y'],p['x'])!=(positions[color]['y'],positions[color]['x'])]
    if len(moved)==1:
     b,a=moved[0];self.actor=a['color'];self.moves[self.last['action']]=dict(delta=[a['y']-b['y'],a['x']-b['x']],source=source,before=b,after=a)
     others=[p for p in self.markers if p['color']!=self.actor]
     if len(others)==1:self.goal=others[0]
   elif self.pending is not None:
    f=self.view;patch=[dict(i=(y-f['y'])*f['w']+x,before=self.previous['frame'][y][x],after=o['frame'][y][x]) for y in range(f['y'],f['y']+f['h']) for x in range(f['w']) if self.previous['frame'][y][x]!=o['frame'][y][x]]
    if patch:
     identity=self.pending['control_id']+':'+digest(patch);self.models[identity]=dict(patch=patch,source=source,button=self.pending,guards=[dict(i=(y-f['y'])*f['w']+x,before=self.previous['frame'][y][x],after=o['frame'][y][x]) for y in range(f['y'],f['y']+f['h']) for x in range(self.field['w'],64)])
  if self.active_waypoint and self.previous is not None:
   old=self.positions(self.previous).get(self.actor);now=positions.get(self.actor)
   if old and now and self.last['action'] in (1,2,3,4):
    self.waypoint_stalls=self.waypoint_stalls+1 if (old['y'],old['x'])==(now['y'],now['x']) else 0
    if self.waypoint_stalls>=2:self.explored_pivots.add(tuple(self.active_waypoint));self.active_waypoint=None
  self.pending=None;action=None;data={};path=None;reason='unresolved_bridge_goal'
  if o['state']=='NOT_FINISHED' and self.steps<240:
   mover=positions.get(self.actor)
   local_context=None if mover is None else [[o['frame'][yy][xx] for xx in range(max(0,mover['x']-2),min(64,mover['x']+4))]for yy in range(max(0,mover['y']-2),min(64,mover['y']+4))]
   for a in (1,2,3,4):
    key='motion'+str(a)+':'+digest(local_context)
    if a not in self.moves and self.attempts.get(key,0)<2:
     action=a;self.attempts[key]=self.attempts.get(key,0)+1;reason='retest_unlearned_motion_in_changed_local_context';break
   if action is None:
    for q in self.buttons:
     mover=positions.get(self.actor);standing=[]
     if mover:standing=[p['control_id'] for p in self.buttons if p['x']<self.field['w'] and p['y']<=mover['y'] and mover['y']+2<=p['y']+p['h'] and p['x']<=mover['x'] and mover['x']+2<=p['x']+p['w']]
     unsafe=False
     if mover:
      occupied={(mover['y']+dy-self.view['y'])*64+mover['x']+dx for dy in (0,1) for dx in (0,1)}
      for m in self.models.values():
       if m['button']['control_id']==q['control_id'] and any(z['i'] in occupied and self.field['color'] in (z['before'],z['after']) for z in m['patch']):unsafe=True
     if unsafe:continue
     contact=bool(mover and q['x']<=mover['x'] and mover['x']+2<=q['x']+q['w'] and q['y']<=mover['y'] and mover['y']+2<=q['y']+q['h'])
     key='switch'+q['control_id']+':'+str(contact)+':'+digest([row[self.field['w']:] for row in o['frame'][self.field['y']:self.field['y']+self.field['h']]])
     if self.attempts.get(key,0)<2:action=6;data=dict(y=q['y']+q['h']//2,x=q['x']+q['w']//2);self.pending=q;reason='learn_reversible_terrain_switch';self.attempts[key]=self.attempts.get(key,0)+1;break
   if action is None and self.actor in positions and self.goal:
    path=self.path(o,positions[self.actor])
    if not path and self.active_waypoint:
     if [positions[self.actor]['y'],positions[self.actor]['x']]==list(self.active_waypoint):self.explored_pivots.add(tuple(self.active_waypoint));self.active_waypoint=None
     else:
      path=self.path(o,positions[self.actor],dict(y=self.active_waypoint[0],x=self.active_waypoint[1]))
      if not path:self.active_waypoint=None
    if not path:
     mover=positions[self.actor]
     standing=[p for p in self.buttons if p['x']<self.field['w'] and p['y']<=mover['y'] and mover['y']+2<=p['y']+p['h'] and p['x']<=mover['x'] and mover['x']+2<=p['x']+p['w']]
     for p in standing:
      for a in (1,2,3,4):
       ident=(p['control_id'],a)
       if ident not in self.pivot_move_tests:self.pivot_move_tests.add(ident);action=a;reason='test_conditional_movement_at_visible_junction';break
      if action is not None:break
    if not path and action is None:
     mover=positions[self.actor];choices=[]
     for q in self.buttons:
      if q['x']>=self.field['w']:continue
      targets=[dict(y=q['y'],x=q['x'])]
      if q['h']<mover['h']*2 or q['w']<mover['w']*2:
       # Contact is an alternative to click: align a small glyph with the learned motion lattice.
       sy=min([abs(m['delta'][0]) for m in self.moves.values() if m['delta'][0]]or[1]);sx=min([abs(m['delta'][1]) for m in self.moves.values() if m['delta'][1]]or[1])
       targets=[dict(y=yy,x=xx)for yy in range(q['y']-mover['h']+1,q['y']+q['h']) for xx in range(q['x']-mover['w']+1,q['x']+q['w']) if (yy-mover['y'])%sy==0 and (xx-mover['x'])%sx==0]
      for target in targets:
       ident=(target['y'],target['x'])
       if (mover['y'],mover['x'])==ident and all((q['control_id'],a) in self.pivot_move_tests for a in (1,2,3,4)):self.explored_pivots.add(ident)
       if ident in self.explored_pivots:continue
       route=self.path(o,mover,target)
       if route:choices.append((len(route),ident,route))
     if choices:
      chosen=min(choices);path=chosen[2];self.active_waypoint=list(chosen[1]);self.waypoint_stalls=0
    if path:
     action,color=path[0];reason='compose_observed_motion_and_terrain_switches'
     if action==6:q=self.models[color]['button'];data=dict(y=q['y']+q['h']//2,x=q['x']+q['w']//2);self.pending=q
  c=None
  if action is not None:
   self.attempts[str(action)]=self.attempts.get(str(action),0)+1;self.steps+=1;c=dict(kind='switch_bridge_hypothesis',context=digest(o),action=action,field=self.view,playfield=self.field,actor=positions.get(self.actor),goal=self.goal,buttons=self.buttons,moves=copy.deepcopy(self.moves),switches=list(copy.deepcopy(self.models).values()),path=path,goal_is_hypothesis=True)
  r=dict(action=action,data=data,done=action is None,certificate=c,advisor='switch_bridge',diagnostics=dict(reason=reason,steps=self.steps,controls=len(self.models)));self.previous=copy.deepcopy(o);self.last=copy.deepcopy(r);return r
