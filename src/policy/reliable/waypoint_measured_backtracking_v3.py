"""Observe failed composition, learn undo, and backtrack through retained alternatives."""
import copy
from waypoint_recursive_inquiry_v15 import Agent as Prefix
from waypoint_failure_recovery_v1 import composition,board_digest
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
def context(obs):return digest(dict(board=obs['frame'][3:62],level=obs['levels_completed']))
def old_options(obs,reach):
 s=composition(obs);tokens=s['tokens'];ps=parts(obs['frame']);requests=[p for p in ps if 3<=p['y']<8 and p['h']==p['w']and p['area']==p['h']**2 and p['h']<=5];goals=[p for p in ps if p['y']>=8 and p['h']==p['w']and 7<=p['h']<=12 and p['area']>=p['h']**2/2]
 center=lambda p:(p['y']+p['h']//2,p['x']+p['w']//2)
 targets=[center(p)for p in goals];needed=max([p['h']for p in requests]or[4]);bestsize=max([p['h']for p in tokens]or[0]);active=[p for p in tokens if p['h']==bestsize];candidates={}
 def add(point,rank,kind,origins):
  if not(10<=point[0]<=60 and 2<=point[1]<=61):return
  item=dict(point=point,rank=rank,kind=kind,origins=origins)
  if point not in candidates or rank<candidates[point]['rank']:candidates[point]=item
 def gd(point):return min((max(abs(point[i]-q[i])for i in(0,1))for q in targets),default=0)
 for ix,p in enumerate(tokens):
  for q in tokens[ix+1:]:
   if p['h']!=q['h']or p['color']!=q['color']:continue
   a,b=center(p),center(q);lo=[max(a[i],b[i])-reach for i in(0,1)];hi=[min(a[i],b[i])+reach for i in(0,1)]
   if any(lo[i]>hi[i]for i in(0,1)):continue
   points={(lo[0],lo[1]),(lo[0],hi[1]),(hi[0],lo[1]),(hi[0],hi[1]),((a[0]+b[0])//2,(a[1]+b[1])//2)}
   for target in targets:points.add(tuple(max(lo[i],min(hi[i],target[i]))for i in(0,1)))
   for point in points:add(point,(-p['h']-3,gd(point),point),'merge_at_shared_observed_reach',[p,q])
 for p in active:
  origin=center(p);mates=[center(q)for q in tokens if q!=p and q['h']==p['h']and q['color']==p['color']];destinations=targets if p['h']>=needed else mates or targets
  for dest in destinations:
   point=tuple(origin[i]+max(-reach,min(reach,dest[i]-origin[i]))for i in(0,1))
   if point!=origin:add(point,(-p['h']-1,max(abs(point[i]-dest[i])for i in(0,1)),point),'move_toward_composition_or_goal',[p])
  for dy in(-reach,0,reach):
   for dx in(-reach,0,reach):
    if not(dy or dx):continue
    point=(origin[0]+dy,origin[1]+dx);distance=min((max(abs(point[i]-q[i])for i in(0,1))for q in destinations),default=0)
    add(point,(-p['h'],distance,point),'alternative_local_move',[p])
 return sorted(candidates.values(),key=lambda p:p['rank']),s,needed
def options(obs,reach,hazard_roles=()):
 from math import sqrt
 choices,s,needed=old_options(obs,reach);tokens=s['tokens'];center=lambda p:(p['y']+p['h']//2,p['x']+p['w']//2)
 ps=parts(obs['frame']);goals=[p for p in ps if p['y']>=8 and p['h']==p['w']and 7<=p['h']<=12 and p['area']>=p['h']**2/2];targets=[center(p)for p in goals]
 def gd(p):return min((sum(abs(p[i]-q[i])for i in(0,1))for q in targets),default=0)
 out={}
 for q in choices:
  p=tuple(q['point']);origins=q['origins']
  if len(origins)==1:
   a=center(origins[0]);d=sqrt(sum((p[i]-a[i])**2 for i in(0,1)))
   if d>reach:p=tuple(a[i]+int((p[i]-a[i])*reach/d)for i in(0,1))
  if all(sum((p[i]-center(o)[i])**2 for i in(0,1))<=reach**2 for o in origins):out[p]=dict(q,point=p)
 for ix,a in enumerate(tokens):
  for b in tokens[ix+1:]:
   if(a['color'],a['h'])!=(b['color'],b['h']):continue
   aa,bb=center(a),center(b);pts=[]
   for y in range(max(10,max(aa[0],bb[0])-reach),min(60,min(aa[0],bb[0])+reach)+1):
    for x in range(max(2,max(aa[1],bb[1])-reach),min(61,min(aa[1],bb[1])+reach)+1):
     p=(y,x)
     if all(sum((p[i]-q[i])**2 for i in(0,1))<=reach**2 for q in(aa,bb)):pts.append(p)
   if not pts:continue
   selected={min(pts,key=lambda p:(gd(p),p)),min(pts),max(pts),min(pts,key=lambda p:(p[1],p[0])),max(pts,key=lambda p:(p[1],p[0]))}
   for p in selected:out[p]=dict(point=p,rank=(-a['h']-3,gd(p),p),kind='merge_within_measured_radial_bound',origins=[a,b])
 hazards=[]
 for role in hazard_roles:
  ink=role['color'];rest={(y,x)for y in range(8,62)for x in range(64)if obs['frame'][y][x]==ink}
  if len(rest)>128:continue
  while rest:
   start=rest.pop();group={start};todo=[start]
   while todo:
    p=todo.pop();near={q for q in rest if max(abs(p[i]-q[i])for i in(0,1))<=2};rest-=near;group|=near;todo.extend(near)
   if len(group)<3:continue
   centerpoint=tuple((min(p[i]for p in group)+max(p[i]for p in group))/2 for i in(0,1));deltas=[max(abs(v)for v in q['delta'])for q in role['evidence']if any(q['delta'])];speed=sorted(deltas)[len(deltas)//2]if deltas else 1
   hazards.append(dict(color=ink,points=sorted(group),center=centerpoint,speed=speed))
 largest=max([p['h']for p in tokens]or[0]);number=sum(p['h']==largest for p in tokens);ranked=[]
 for candidate in out.values():
  origins=candidate['origins'];point=candidate['point'];merging=len(origins)>1
  if max(p['h']for p in origins)<largest and(number>=2 or not merging or origins[0]['h']+1<largest):continue
  future=[center(p)for p in tokens if p not in origins and p['h']>1]+[point];margins=[]
  for hazard in hazards:
   at=hazard['center'];target=min(future,key=lambda q:(sum((q[i]-at[i])**2 for i in(0,1)),q));speed=hazard['speed'];predicted=tuple(at[i]+max(-speed,min(speed,target[i]-at[i]))for i in(0,1));margins.extend(max(abs(predicted[i]-q[i])for i in(0,1))for q in future)
  safety=min(margins)if margins else 20;priority=-origins[0]['h']-3 if merging else-origins[0]['h']-1
  rank=(int(safety<3),-min(12,safety),priority,gd(point),point)if hazards else(priority,gd(point),point)
  ranked.append(dict(candidate,rank=rank,hazards=hazards,predicted_minimum_separation=safety,risk_is_hypothesis=True))
 return sorted(ranked,key=lambda p:p['rank']),s,needed
class Agent:
 def __init__(self):
  self.prefix=Prefix();self.previous=None;self.last=None;self.stack=[];self.pending=None;self.own=False;self.disabled=False;self.level=None;self.t=0;self.tried={};self.failures=[];self.rollbacks=[];self.reach=3;self.reach_evidence=[];self.active=True;self.retries=0;self.range_support=None;self.hazard_roles=[]
 def respond(self,obs):
  if obs['state']=='GAME_OVER'and self.retries<3 and self.t<512:
   self.retries+=1;self.pending=None;self.stack=[];self.previous=None;self.last=None;self.own=True;self.disabled=False
   return self.emit(obs,dict(done=False,action=0,data={},certificate=dict(kind='waypoint_retained_retry',context=digest(obs),attempt=self.retries,retained_failures=copy.deepcopy(self.failures),retained_contexts=len(self.tried),retained_trials=sum(len(v)for v in self.tried.values())),advisor='waypoint_backtracking',diagnostics=dict(reason='retry_retaining_rejected_alternatives',attempt=self.retries)))
  event=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs))if self.previous is not None else None
  lost=False
  if self.level!=obs['levels_completed']:
   if self.own:self.prefix.previous=None;self.prefix.prior.prior.previous=None
   self.level=obs['levels_completed'];self.stack=[];self.pending=None;self.own=False
  elif event and self.pending:
   restored=board_digest(obs)==self.pending['expected_board']
   self.rollbacks.append(dict(source=digest(event),failure_source=self.pending['source'],restored=restored,expected_board=self.pending['expected_board'],observed_board=board_digest(obs)))
   if not restored:self.disabled=True
   self.pending=None
  elif event and self.last['action']==6:
   before=composition(self.previous);after=composition(obs);lost=before['palette']==after['palette']and after['mass']<before['mass']
   row=dict(source=digest(event),level=self.level,click=copy.deepcopy(self.last['data']),before=before,after=after,expected_board=board_digest(self.previous),prior_context=context(self.previous),lost=lost)
   self.stack.append(row)
   if lost:self.failures.append(copy.deepcopy(row))
  if self.disabled or self.t>=512 or obs['state']!='NOT_FINISHED':return dict(done=True,action=None,data={},certificate=None,advisor='waypoint_backtracking',diagnostics=dict(reason='bounded_search_stopped',failures=len(self.failures),rollbacks=len(self.rollbacks)))
  r=None
  if not self.own:
   r=self.prefix.respond(obs);c=r.get('certificate')or{};hazards=c.get('moving_sprite_evidence',[])
   if hazards:self.hazard_roles=copy.deepcopy(hazards)
   if lost and hazards and 7 in obs['available_actions']:
    self.own=True;self.reach_evidence=copy.deepcopy(c.get('retained_reach_evidence',[]));self.reach=max([max(abs(v)for v in p['delta'])for p in self.reach_evidence]+[self.range_support['distance']if self.range_support else 3])
   else:return self.emit(obs,r)
  if lost:return self.undo(obs,'undo_observed_composition_loss')
  key=context(obs)
  # Repeated local failures justify revisiting the preceding decision, while
  # retaining every rejected option for later retries. This is a bounded search
  # allocation hypothesis, not a proof that all other choices fail.
  failures_here=sum(p['prior_context']==key for p in self.failures)
  if failures_here>=3 and self.stack:return self.undo(obs,'backtrack_after_repeated_local_failures')
  choices,scene,needed=options(obs,self.reach,self.hazard_roles);tried=self.tried.setdefault(key,set());candidate=next((q for q in choices if q['point']not in tried),None)
  if candidate:
   point=candidate['point'];tried.add(point);c=dict(kind='waypoint_backtracking',context=digest(obs),tag='test_retained_alternative',candidate=copy.deepcopy(candidate),scene=scene,reach=self.reach,reach_evidence=copy.deepcopy(self.reach_evidence),retained_failures=copy.deepcopy(self.failures),rollback_outcomes=copy.deepcopy(self.rollbacks),prior_trials=sorted(tried),goal_is_hypothesis=True)
   return self.emit(obs,dict(done=False,action=6,data=dict(y=point[0],x=point[1]),certificate=c,advisor='waypoint_backtracking',diagnostics=dict(reason=c['tag'],choices=len(choices),tried=len(tried),depth=len(self.stack))))
  return self.undo(obs,'backtrack_after_local_alternatives_exhausted')
 def undo(self,obs,tag):
  if not self.stack or 7 not in obs['available_actions']:return dict(done=True,action=None,data={},certificate=None,advisor='waypoint_backtracking',diagnostics=dict(reason='no_reversible_parent'))
  p=self.stack.pop();self.tried.setdefault(p['prior_context'],set()).add((p['click']['y'],p['click']['x']));self.pending=copy.deepcopy(p)
  c=dict(kind='waypoint_backtracking',context=digest(obs),tag=tag,undo=copy.deepcopy(p),retained_failures=copy.deepcopy(self.failures),rollback_outcomes=copy.deepcopy(self.rollbacks),goal_is_hypothesis=True)
  return self.emit(obs,dict(done=False,action=7,data={},certificate=c,advisor='waypoint_backtracking',diagnostics=dict(reason=tag,depth=len(self.stack))))
 def emit(self,obs,r):
  if r.get('certificate')and self.range_support:r['certificate']['range_support']=copy.deepcopy(self.range_support)
  if r.get('certificate')and self.hazard_roles:r['certificate']['hazard_role_support']=copy.deepcopy(self.hazard_roles)
  self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r)
  if not r['done']:self.t+=1
  return r
