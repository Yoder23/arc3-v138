"""Infer independent line constraints from contact failures, then compose multi-part motion."""
import copy,heapq
from collections import Counter
from shape_footprint_planner_v6 import Agent as Prior
from visual_transform_learner import digest

def lines(obs,color,targets):
 ps={(y,x) for y,row in enumerate(obs['frame'][:62]) for x,c in enumerate(row) if c==color}-set(map(tuple,targets));rows=Counter(y for y,x in ps);cols=Counter(x for y,x in ps)
 if not rows or not cols:return None
 y,n=rows.most_common(1)[0];x,m=cols.most_common(1)[0]
 if min(n,m)<17 or sum(v>=17 for v in rows.values())!=1 or sum(v>=17 for v in cols.values())!=1:return None
 hh=sorted(b for a,b in ps if a==y);vv=sorted(a for a,b in ps if b==x)
 if (hh[0]+hh[-1])%2 or (vv[0]+vv[-1])%2:return None
 h=(y,(hh[0]+hh[-1])//2);v=((vv[0]+vv[-1])//2,x);r=((hh[-1]-hh[0])//2,(vv[-1]-vv[0])//2)
 if min(r)<8:return None
 hp={(h[0],b) for b in range(hh[0],hh[-1]+1)};vp={(a,v[1]) for a in range(vv[0],vv[-1]+1)}
 if len(hp&ps)<.85*len(hp) or len(vp&ps)<.85*len(vp):return None
 return dict(color=color,h=h,v=v,radii=r,h_points=sorted(hp&ps),v_points=sorted(vp&ps))
def pixels(at,radii):
 hy,hx,vy,vx=at;rh,rv=radii;return ({(hy,hx+d) for d in range(-rh,rh+1)},{(vy+d,vx) for d in range(-rv,rv+1)})
def transition(at,action,models,radii,site):
 delta=models[action]['delta'];out=list(at)
 for j,pts in enumerate(pixels(at,radii)):
  shifted={(y+delta[0],x+delta[1]) for y,x in pts}
  if not shifted&site:out[2*j]+=delta[0];out[2*j+1]+=delta[1]
 return tuple(out)
class Agent:
 def __init__(self):self.prior=Prior();self.active=False;self.color=None;self.previous=None;self.last=None;self.support=[];self.steps=0;self.refutations=[];self.level=None;self.finished=False;self.boundary_revisions=[]
 def respond(self,obs):
  if self.finished:return self.prior.respond(obs)
  if not self.active:
   r=self.prior.respond(obs)
   if self.prior.planning:
    for color,targets in self.prior.targets.items():
     q=lines(obs,color,targets)
     if q and (q['h'][0]!=q['v'][0] or q['h'][1]!=q['v'][1]):self.active=True;self.color=color;self.level=obs['levels_completed'];break
   if not self.active:return r
  targets=self.prior.targets[self.color];q=lines(obs,self.color,targets);site=self.prior.prior.site;models={a:m for a,m in self.prior.prior.models.items() if len({tuple(p['origin']) for p in m['support']})>=2};action=None;reason='unresolved_articulated_geometry';path=[]
  if q and self.last and q['radii']!=self.last['certificate']['lines']['radii']:q=None
  if q is None and self.previous is not None and self.last is not None:
   old=self.last['certificate']['lines'];at=tuple(old['h'])+tuple(old['v']);pred=transition(at,self.last['action'],models,old['radii'],set(map(tuple,site['points'])));pp=pixels(pred,old['radii']);observed=[];valid=True
   from shape_site_inquiry_v3 import scene
   occluders=[o for o in scene(obs)[0] if o['color']!=self.color and o['geometry']['kind']=='rectangle'];occluded={(y,x) for o in occluders for y,x in o['boundary_points'] if obs['frame'][y][x]==o['color']}
   for pts in pp:
    expected={p for p in pts if 0<=p[0]<62 and 0<=p[1]<64};support={p for p in expected if obs['frame'][p[0]][p[1]]==self.color};missing=expected-support;badge={p for p in missing if obs['frame'][p[0]][p[1]]==0};valid &= len(support)>=12 and len(support)>=.6*len(expected) and len(badge)<=1 and missing<=occluded|badge;observed.append(sorted(support))
   if valid:
    q=dict(color=self.color,h=pred[:2],v=pred[2:],radii=old['radii'],h_points=observed[0],v_points=observed[1],clipping_hypothesis=True,occluders=copy.deepcopy(occluders));self.boundary_revisions.append(dict(source=digest(dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs))),interpretation='Visible clipping does not establish blocked movement'))
  if self.previous is not None and self.last is not None:
   old=self.last['certificate']['lines'];event=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs))
   if old and q and old['radii']==q['radii']:
    at=tuple(old['h'])+tuple(old['v']);actual=tuple(q['h'])+tuple(q['v']);pred=transition(at,self.last['action'],models,old['radii'],set(map(tuple,site['points'])));row=dict(source=digest(event),before=old,after=q,predicted=pred)
    if actual==pred:self.support.append(row)
    else:self.refutations.append(row)
  if q and obs['state']=='NOT_FINISHED' and obs['levels_completed']==self.level and self.steps<160 and not self.refutations:
   at=tuple(q['h'])+tuple(q['v']);sites=set(map(tuple,site['points']));blocked=[p for p in self.support if tuple(p['before']['h'])==tuple(p['after']['h']) or tuple(p['before']['v'])==tuple(p['after']['v'])]
   if len(blocked)<2:
    options=[]
    for a in models:
     nxt=transition(at,a,models,q['radii'],sites)
     if nxt!=at and (nxt[:2]==at[:2] or nxt[2:]==at[2:]):options.append(a)
    if options:action=min(options);reason='test_independent_component_blocking'
   else:
    goalset=set(map(tuple,targets));rh,rv=q['radii'];goalstates=[]
    for hy in {y for y,x in goalset}:
     for vx in {x for y,x in goalset}:
      assignedh=[x for y,x in goalset if y==hy];assignedv=[y for y,x in goalset if x==vx]
      if not all(y==hy or x==vx for y,x in goalset):continue
      for hx in range(at[1]%abs(models[3]['delta'][1]),64,abs(models[3]['delta'][1])):
       for vy in range(at[2]%abs(models[1]['delta'][0]),62,abs(models[1]['delta'][0])):
        g=(hy,hx,vy,vx)
        if goalset<=set.union(*pixels(g,q['radii'])) and all(0<=y<62 and 0<=x<64 for pts in pixels(g,q['radii']) for y,x in pts):goalstates.append(g)
    def estimate(s):return min((max(abs(s[0]-g[0])+abs(s[1]-g[1]),abs(s[2]-g[2])+abs(s[3]-g[3]))//3 for g in goalstates),default=1000)
    heap=[(estimate(at),0,at,[])];cost={at:0};expanded=0
    while heap and expanded<100000:
     _,depth,here,route=heapq.heappop(heap)
     if depth!=cost[here]:continue
     if goalset<=set.union(*pixels(here,q['radii'])):path=route;break
     expanded+=1
     for a in sorted(models):
      nxt=transition(here,a,models,q['radii'],sites)
      if nxt!=here and all(0<=y<62 and 0<=x<64 for pts in pixels(nxt,q['radii']) for y,x in pts) and depth+1<cost.get(nxt,999):cost[nxt]=depth+1;heapq.heappush(heap,(depth+1+estimate(nxt),depth+1,nxt,route+[a]))
    if path:action=path[0];reason='compose_independently_blocked_line_motion'
    elif goalset<=set.union(*pixels(at,q['radii'])):
     self.finished=True;self.prior.placed.add(self.color);self.prior.sequence=None;self.prior.probe_color=None;self.prior.probed.add(self.color);self.prior.previous=None;self.prior.last=None;action=5;reason='restore_remaining_object_after_articulated_goal'
  cert=None
  if action is not None:
   self.steps+=1;cert=dict(kind='articulated_line_hypothesis',context=digest(obs),action=action,lines=q,site=site,models=models,targets=targets,goal_source=self.prior.goal_source,path=path,support=copy.deepcopy(self.support),goal_is_hypothesis=True)
  r=dict(action=action,data={},done=action is None,certificate=cert,advisor='articulated_line_planner',diagnostics=dict(reason=reason,steps=self.steps,support=len(self.support),refutations=copy.deepcopy(self.refutations)));self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r);return r
