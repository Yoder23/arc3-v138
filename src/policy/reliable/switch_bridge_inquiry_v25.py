"""Learn movement and switch-induced terrain patches, then plan over joint position and terrain."""
import copy
from collections import deque
from visible_components_v1 import parts
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.level=None;self.field=None;self.actor=None;self.goal=None;self.markers=[];self.buttons=[];self.moves={};self.models={};self.attempts={};self.previous=None;self.last=None;self.pending=None;self.effects=[];self.steps=0;self.knowledge=[];self.explored_pivots=set();self.pivot_move_tests=set();self.active_waypoint=None;self.waypoint_stalls=0;self.special_sites={};self.transports={};self.no_effect_clicks=[];self.blocked_floors=[];self.control_blocks=[];self.cycle_closed=set()
 def find(self,o):
  ps=parts(o['frame']);fields=[p for p in ps if p['x']==0 and 20<=p['w']<48 and 20<=p['h']<=63]
  if len(fields)!=1:return
  p=fields[0];self.field={k:p[k] for k in ['x','y','w','h','color']};colors={v for row in o['frame'][p['y']:p['y']+p['h']] for v in row[:p['w']]};self.markers=[q for q in ps if q['h']==q['w']==2 and q['area']==4 and q['x']<p['w'] and p['y']<=q['y']<p['y']+p['h']];self.buttons=[q for q in ps if q['x']>=p['w'] and q['color'] in colors and 20<=q['area']<=200 and q['area']>.6*q['h']*q['w']]
  tiles=[q for q in ps if q['x']<p['w'] and q['y']>=p['y'] and q['h']==q['w']==4 and q['area']==16];counts={c:sum(q['color']==c for q in tiles) for c in colors};platform=max(counts,key=counts.get)
  self.buttons += [q for q in tiles if q['color']!=platform]
  self.buttons += [q for q in ps if q['x']<p['w'] and q['y']>=p['y'] and q['color']!=platform and q['area']==q['h']*q['w'] and ((q['h']==4 and q['w']>4) or (q['w']==4 and q['h']>4)) and q not in self.buttons]
  self.buttons += [q for q in ps if q['x']<p['w'] and p['y']<=q['y'] and q['y']+q['h']<=p['y']+p['h'] and q['color'] not in (platform,p['color']) and 4<=q['area']<=8 and sorted((q['h'],q['w']))==[2,4] and q not in self.buttons]
  # A small multicolor mark embedded in a platform may require contact.
  for tile in ps:
   if tile['color']!=platform or tile['w']!=4 or tile['h']!=4 or tile['area']<8 or tile['x']>=p['w'] or tile['y']<p['y']:continue
   foreign=[(yy,xx,o['frame'][yy][xx])for yy in range(tile['y'],tile['y']+4)for xx in range(tile['x'],tile['x']+4)if o['frame'][yy][xx] not in (platform,p['color'])]
   if len(foreign)!=4 or len({c for y,x,c in foreign})<2:continue
   yy=min(y for y,x,c in foreign);xx=min(x for y,x,c in foreign)
   if max(y for y,x,c in foreign)-yy!=1 or max(x for y,x,c in foreign)-xx!=1:continue
   self.buttons.append(dict(y=yy,x=xx,h=2,w=2,area=4,color=min(c for y,x,c in foreign),shape=[(y-yy,x-xx)for y,x,c in foreign],kind='multicolor_contact_hypothesis'))
  for q in self.buttons:
   if q.get('kind')=='multicolor_contact_hypothesis':self.special_sites[(q['y'],q['x'])]=dict(q,source=digest(o),colors=[[o['frame'][q['y']+dy][q['x']+dx]for dx in range(2)]for dy in range(2)])
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
   if len(variants)>256:return None
   for color,m in sorted(self.models.items()):
    for reverse in [False]:
     patch=m['patch'];old='after' if reverse else 'before';new='before' if reverse else 'after'
     if all(v[q['i']]==q[old] for q in patch) and all(v[q['i']]==q[old] for q in m.get('guards',[])):
      nxt=list(v)
      for q in patch:nxt[q['i']]=q[new]
      nxt=tuple(nxt)
      if nxt not in index:index[nxt]=len(variants);variants.append(nxt)
      links[(k,color)]=index[nxt]
  def valid(y,x,k):return f['y']<=y and x>=0 and y+2<=f['y']+h and x+2<=self.field['w'] and all(variants[k][(y+dy-f['y'])*w+x+dx] not in {f['color']}|{m['target_color']for m in self.blocked_floors} for dy in (0,1) for dx in (0,1))
  start=(actor['y'],actor['x'],0);queue=deque([(start,[])]);seen={start}
  while queue:
   (y,x,k),path=queue.popleft()
   if [y,x]==[target['y'],target['x']]:return path
   for action,m in sorted(self.moves.items()):
    yy,xx=y+m['delta'][0],x+m['delta'][1];node=(yy,xx,k)
    if node not in seen and valid(yy,xx,k):seen.add(node);queue.append((node,path+[(action,None)]))
   for color in sorted(self.models):
    control=self.models[color]['button']['control_id']
    if any(b['button']['control_id']==control for b in self.control_blocks):
     affected={p['i']for m in self.models.values()if m['button']['control_id']==control for p in m['patch']if p['i']%64<self.field['w']}
     if any((y+dy-f['y'])*64+x+dx in affected for dy in(0,1)for dx in(0,1)):continue
    if any((m['before']['y'],m['before']['x'])==(y,x)and m['button']['control_id']==self.models[color]['button']['control_id']for m in self.transports.values()):continue
    kk=links.get((k,color));node=(y,x,kk)
    if kk is not None and node not in seen and valid(y,x,kk):seen.add(node);queue.append((node,path+[(6,color)]))
   for identity,m in sorted(self.transports.items()):
    if (m['before']['y'],m['before']['x'])!=(y,x):continue
    yy,xx=m['after']['y'],m['after']['x'];node=(yy,xx,k)
    if node not in seen and valid(yy,xx,k):seen.add(node);queue.append((node,path+[(6,identity)]))
  return None
 def respond(self,o):
  if self.level!=o['levels_completed']:
   retained_moves=copy.deepcopy(self.moves);retained_actor=self.actor;retained_goal=copy.deepcopy(self.goal)
   self.knowledge.append(dict(field=copy.deepcopy(self.field),moves=copy.deepcopy(self.moves),switches=copy.deepcopy(self.models),transports=copy.deepcopy(self.transports)));self.level=o['levels_completed'];self.field=None;self.actor=None;self.goal=None;self.moves={};self.models={};self.attempts={};self.previous=None;self.pending=None;self.steps=0;self.explored_pivots=set();self.pivot_move_tests=set();self.active_waypoint=None;self.waypoint_stalls=0;self.special_sites={};self.transports={};self.blocked_floors=[];self.control_blocks=[];self.cycle_closed=set();self.find(o)
   current=self.positions(o)
   if retained_actor in current:
    self.actor=retained_actor;self.moves=retained_moves
    if retained_goal and retained_goal['color']in current:self.goal=current[retained_goal['color']]
    else:
     others=[q for color,q in current.items()if color!=self.actor]
     if len(others)==1:self.goal=others[0]
  if not self.field:return dict(action=None,data={},done=True,certificate=None,advisor='switch_bridge',diagnostics=dict(reason='no_bounded_field'))
  self.find(o)
  positions=self.positions(o)
  if self.previous is not None:
   e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(o));source=digest(e);self.effects.append(dict(source=source,progress=o['levels_completed']>self.previous['levels_completed'] or o['state']=='WIN'))
   if self.last['action'] in (1,2,3,4):
    old=self.positions(self.previous);moved=[(p,positions[color]) for color,p in old.items() if color in positions and (p['y'],p['x'])!=(positions[color]['y'],positions[color]['x'])]
    if not moved and self.actor in old and self.actor in positions and self.last['action']in self.moves:
     b=old[self.actor];a=positions[self.actor];motion=self.moves[self.last['action']];dy,dx=motion['delta'];yy,xx=b['y']+dy,b['x']+dx
     if (b['y'],b['x'])==(a['y'],a['x']) and 0<=xx and xx+2<=self.field['w']and self.field['y']<=yy and yy+2<=self.field['y']+self.field['h']:
      values={self.previous['frame'][yy+y][xx+x]for y in (0,1)for x in (0,1)}
      if len(values)==1 and self.actor not in values and self.field['color']not in values:self.blocked_floors.append(dict(source=source,action=self.last['action'],actor=copy.deepcopy(b),motion=copy.deepcopy(motion),target=dict(y=yy,x=xx),target_color=next(iter(values)),hypothesis=True))
    if len(moved)==1:
     b,a=moved[0];self.actor=a['color'];self.moves[self.last['action']]=dict(delta=[a['y']-b['y'],a['x']-b['x']],source=source,before=b,after=a)
     others=[p for p in self.markers if p['color']!=self.actor]
     if len(others)==1:self.goal=others[0]
   elif self.pending is not None:
    old=self.positions(self.previous);changed=[(old[c],positions[c])for c in old if c in positions and (old[c]['y'],old[c]['x'])!=(positions[c]['y'],positions[c]['x'])];ignored=set()
    if len(changed)==1 and changed[0][0]['color']==self.actor:
     b,a=changed[0];identity='transport:'+self.pending['control_id']+':'+str((b['y'],b['x'],a['y'],a['x']))
     self.transports[identity]=dict(source=source,button=copy.deepcopy(self.pending),before=b,after=a,field=copy.deepcopy(self.view))
     ignored={(q['y']+dy-self.view['y'])*64+q['x']+dx for q in (b,a)for dy in (0,1)for dx in (0,1)}
    f=self.view;patch=[dict(i=(y-f['y'])*f['w']+x,before=self.previous['frame'][y][x],after=o['frame'][y][x]) for y in range(f['y'],f['y']+f['h']) for x in range(f['w']) if self.previous['frame'][y][x]!=o['frame'][y][x]]
    if not patch and self.pending['x']>=self.field['w'] and self.actor in old:
     actor=old[self.actor];occupied={(actor['y']+dy-self.view['y'])*64+actor['x']+dx for dy in(0,1)for dx in(0,1)}
     cells={p['i']for m in self.models.values()if m['button']['control_id']==self.pending['control_id']for p in m['patch']if p['i']%64<self.field['w']}
     if occupied&cells:self.control_blocks.append(dict(source=source,button=copy.deepcopy(self.pending),actor=copy.deepcopy(actor),field=copy.deepcopy(self.view),hypothesis=True))
    if not patch and self.pending['x']<self.field['w']:
     self.no_effect_clicks.append(dict(source=source,button=copy.deepcopy(self.pending),field=copy.deepcopy(self.view),role=[self.pending['h'],self.pending['w'],self.pending['area'],self.pending.get('kind')]))
    patch=[q for q in patch if q['i'] not in ignored]
    if patch:
     prior_models=[m for m in self.models.values()if m['button']['control_id']==self.pending['control_id']]
     if len(prior_models)>=2 and any(m['patch']==patch for m in prior_models):self.cycle_closed.add(self.pending['control_id'])
     identity=self.pending['control_id']+':'+digest(patch);self.models[identity]=dict(patch=patch,source=source,button=self.pending,ignored_actor_cells=sorted(ignored),guards=[dict(i=(y-f['y'])*f['w']+x,before=self.previous['frame'][y][x],after=o['frame'][y][x]) for y in range(self.pending['y'],self.pending['y']+self.pending['h']) for x in range(self.pending['x'],self.pending['x']+self.pending['w'])])
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
     role=[q['h'],q['w'],q['area'],q.get('kind')]
     failures={m['button']['control_id']for m in self.no_effect_clicks if m['role']==role}
     external_control=any(m['button']['x']>=self.field['w']for m in self.models.values())
     if q['x']<self.field['w'] and external_control and len(failures)>=2:continue
     mover=positions.get(self.actor);standing=[]
     if mover and any(t['button']['control_id']==q['control_id'] and (t['before']['y'],t['before']['x'])==(mover['y'],mover['x']) for t in self.transports.values()):continue
     if mover:standing=[p['control_id'] for p in self.buttons if p['x']<self.field['w'] and p['y']<=mover['y'] and mover['y']+2<=p['y']+p['h'] and p['x']<=mover['x'] and mover['x']+2<=p['x']+p['w']]
     unsafe=False
     if mover:
      occupied={(mover['y']+dy-self.view['y'])*64+mover['x']+dx for dy in (0,1) for dx in (0,1)}
      for m in self.models.values():
       if m['button']['control_id']==q['control_id'] and any(z['i'] in occupied and self.field['color'] in (z['before'],z['after']) for z in m['patch']):unsafe=True
     if mover and any(b['button']['control_id']==q['control_id']for b in self.control_blocks):
      affected={p['i']for m in self.models.values()if m['button']['control_id']==q['control_id']for p in m['patch']if p['i']%64<self.field['w']}
      if occupied&affected:unsafe=True
     if unsafe:continue
     contact=bool(mover and q['x']<=mover['x'] and mover['x']+2<=q['x']+q['w'] and q['y']<=mover['y'] and mover['y']+2<=q['y']+q['h'])
     special=tuple(sorted((yy,xx)for yy,xx in self.special_sites if mover and (mover['y'],mover['x'])==(yy,xx)))
     related=[m for m in self.models.values()if m['button']['control_id']==q['control_id']]
     cyclic=len(related)>=2 and not any({(p['i'],p['after'],p['before'])for p in a['patch']}=={(p['i'],p['before'],p['after'])for p in b['patch']}for i,a in enumerate(related)for b in related[i+1:])
     effect_context=[]
     if cyclic:
      cells=sorted({p['i']for m in related for p in m['patch']})
      effect_context=[(i,o['frame'][i//64+self.view['y']][i%64])for i in cells]
     key='switch'+q['control_id']+':'+str((contact,special))+':'+digest([row[q['x']:q['x']+q['w']]for row in o['frame'][q['y']:q['y']+q['h']]])+(':'+digest(effect_context)if cyclic else '')
     if cyclic and q['control_id']in self.cycle_closed:continue
     if cyclic and sum(v for k,v in self.attempts.items()if k.startswith('switch'+q['control_id']+':'))>=20:continue
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
     if action==6:q=(self.models.get(color)or self.transports[color])['button'];data=dict(y=q['y']+q['h']//2,x=q['x']+q['w']//2);self.pending=q
  c=None
  if action is not None:
   self.attempts[str(action)]=self.attempts.get(str(action),0)+1;self.steps+=1;c=dict(kind='switch_bridge_hypothesis',context=digest(o),action=action,field=self.view,playfield=self.field,actor=positions.get(self.actor),goal=self.goal,buttons=self.buttons,moves=copy.deepcopy(self.moves),switches=list(copy.deepcopy(self.models).values()),path=path,goal_is_hypothesis=True,special_sites=list(copy.deepcopy(self.special_sites).values()),transports=list(copy.deepcopy(self.transports).values()),no_effect_clicks=copy.deepcopy(self.no_effect_clicks),blocked_floors=copy.deepcopy(self.blocked_floors),control_blocks=copy.deepcopy(self.control_blocks))
  r=dict(action=action,data=data,done=action is None,certificate=c,advisor='switch_bridge',diagnostics=dict(reason=reason,steps=self.steps,controls=len(self.models)));self.previous=copy.deepcopy(o);self.last=copy.deepcopy(r);return r
