"""Infer joint rectangle motion from clicks, then compose actions around visible barriers."""
import copy,heapq
from collections import Counter
from endpoint_extension_inquiry_v2 import Agent as Prior
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
def key(p):return str(p['color'])+':'+str(tuple(map(tuple,p['shape'])))
def scene(obs):
 ps=parts(obs['frame']);f=obs['frame'];background=Counter(v for row in f for v in row).most_common(1)[0][0];buttons=[p for p in ps if p['h']==p['w']==3 and p['area']==7];colors=sorted({p['color'] for p in buttons});bodies=[];endpoint=None;marker=None
 for color in colors:
  candidates=[p for p in ps if p['color']==color and p not in buttons and (p['h']==3 or p['w']==3) and p['area']>=5]
  if len(candidates)!=1:return None
  p=candidates[0];holes=[(y,x,f[y][x]) for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w']) if f[y][x]!=color]
  if len(holes)>1:return None
  if holes:endpoint=list(holes[0][:2]);marker=holes[0][2]
  roots=[]
  for q in ps:
   if q['area']!=3 or q['color']==color:continue
   if q['h']==3 and q['w']==1 and p['h']==3 and q['y']==p['y']:
    if q['x']+1==p['x']:roots.append([-1,0])
    elif p['x']+p['w']==q['x']:roots.append([1,0])
   if q['h']==1 and q['w']==3 and p['w']==3 and q['x']==p['x']:
    if q['y']+1==p['y']:roots.append([0,-1])
    elif p['y']+p['h']==q['y']:roots.append([0,1])
  if len(roots)!=1:return None
  bodies.append(dict(color=color,part=p,root=roots[0]))
 if endpoint is None or len(bodies)<3:return None
 goals=[]
 for y in range(1,53):
  for x in range(1,63):
   if f[y][x]==background and all(f[y+dy][x+dx]==marker for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]):goals.append([y,x])
 walls=[]
 for p in ps:
  if p['y']<54 and p['color'] not in colors+[marker] and p['area']>=20 and max(p['h'],p['w'])>=8:
   walls.extend([[p['y']+y,p['x']+x] for y,x in p['shape']])
 state=tuple(v for b in bodies for v in [b['part']['y'],b['part']['x'],b['part']['h'],b['part']['w']])+tuple(endpoint)
 return dict(bodies=bodies,buttons=buttons,endpoint=endpoint,marker=marker,goals=goals,walls=walls,state=state)
def valid(state,sc):
 wall=set(map(tuple,sc['walls']))
 for i,b in enumerate(sc['bodies']):
  y,x,h,w=state[4*i:4*i+4]
  if min(h,w)<2 or y<1 or x<1 or y+h>=54 or x+w>=63 or (h!=3 and w!=3):return False
  pixels={(yy,xx) for yy in range(y,y+h) for xx in range(x,x+w)};rx,ry=b['root']
  if rx:pixels|={(yy,x-1 if rx<0 else x+w) for yy in range(y,y+h)}
  if ry:pixels|={(y-1 if ry<0 else y+h,xx) for xx in range(x,x+w)}
  if pixels&wall:return False
 return True
def plan(sc,models):
 if len(sc['goals'])!=1:return None
 start=tuple(sc['state']);goal=sc['goals'][0];h=lambda s:(abs(s[-2]-goal[0])+abs(s[-1]-goal[1]))/3;queue=[(h(start),0,start,[])];cost={start:0};expanded=0
 while queue and expanded<60000:
  _,g,s,path=heapq.heappop(queue)
  if g!=cost[s]:continue
  expanded+=1
  if list(s[-2:])==goal:return path
  for k,m in sorted(models.items()):
   if len(m['support'])<2:continue
   nxt=tuple(a+b for a,b in zip(s,m['delta']))
   if not valid(nxt,sc) or cost.get(nxt,10**9)<=g+1:continue
   cost[nxt]=g+1;heapq.heappush(queue,(g+1+h(nxt),g+1,nxt,path+[k]))
 return None
class Agent:
 def __init__(self):self.prior=Prior();self.active=False;self.level=None;self.previous=None;self.pending=None;self.models={};self.tried={};self.steps=0;self.failed=[]
 def respond(self,obs):
  if self.level!=obs['levels_completed']:
   if self.active:self.prior.previous=None;self.prior.last=None;self.prior.pending=None
   self.level=obs['levels_completed'];self.active=False;self.pending=None;self.models={};self.tried={};self.steps=0
  sc=scene(obs)
  if not self.active:
   r=self.prior.respond(obs)
   if not r['done'] or not sc or obs['state']!='NOT_FINISHED':return r
   self.active=True
  if not sc or obs['state']!='NOT_FINISHED':return dict(action=None,data={},done=True,certificate=None,advisor='chain_endpoint',diagnostics=dict(reason='unresolved_joint_visibility'))
  if self.pending:
   old,p=self.pending;e=dict(before=self.previous,action=6,data=dict(y=p['y']+1,x=p['x']+1),after=copy.deepcopy(obs));source=digest(e);k=key(p);delta=[b-a for a,b in zip(old['state'],sc['state'])]
   if any(delta):
    prior=self.models.get(k)
    if not prior or prior['delta']!=delta:self.models[k]=dict(delta=delta,support=[])
    self.models[k]['support'].append(dict(source=source,before=old,after=sc,button=p))
   else:self.failed.append(dict(source=source,button=p))
  self.pending=None;p=None;path=None;reason='unresolved_joint_motion'
  if self.steps<240:
   for q in sc['buttons']:
    k=key(q)
    if self.tried.get(k,0)<1:p=q;reason='test_joint_click_effect';break
   if p is None:
    path=plan(sc,self.models)
    if path:p=next(q for q in sc['buttons'] if key(q)==path[0]);reason='compose_observed_joint_motion_around_barriers'
    else:
     candidates=[q for q in sc['buttons'] if len(self.models.get(key(q),{}).get('support',[]))<2 and self.tried.get(key(q),0)<5]
     if candidates:p=min(candidates,key=lambda q:(self.tried.get(key(q),0),key(q)));reason='confirm_joint_motion_from_another_configuration'
  c=None;data={};action=None
  if p:
   action=6;data=dict(y=p['y']+1,x=p['x']+1);self.tried[key(p)]=self.tried.get(key(p),0)+1;self.steps+=1;c=dict(kind='joint_endpoint_hypothesis',context=digest(obs),action=6,scene=sc,button=p,models=copy.deepcopy(self.models),path=path,failed=copy.deepcopy(self.failed),goal_is_hypothesis=True);self.pending=(copy.deepcopy(sc),copy.deepcopy(p));self.previous=copy.deepcopy(obs)
  return dict(action=action,data=data,done=p is None,certificate=c,advisor='chain_endpoint',diagnostics=dict(reason=reason,steps=self.steps,models=len(self.models)))
