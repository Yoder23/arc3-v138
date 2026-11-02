"""Compose directional paint hypotheses; retain observed tool transitions and verify effects."""
import copy,math
from collections import deque
from stencil_goal_inquiry_v3 import Agent as Prior
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
DIRECTIONS=[(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1)]
def orient(tool,canvas):
 points=[(tool['y']+y,tool['x']+x) for y,x in tool['shape']];v=[sum(p[i] for p in points)/len(points)-(canvas['y' if i==0 else 'x']+(canvas['h' if i==0 else 'w']-1)/2) for i in (0,1)]
 return max(DIRECTIONS,key=lambda d:sum(x*y for x,y in zip(d,v))/math.hypot(*d))
def masks(h,w):
 return {d:tuple(i for i in range(h*w) if d[0]*(2*(i//w)-h+1)+d[1]*(2*(i%w)-w+1)>=0) for d in DIRECTIONS}
def compose(current,target,h,w,ms=None):
 ms=masks(h,w) if ms is None else ms;start=tuple(target);queue=deque([(start,[])]);seen={start}
 while queue and len(seen)<30000:
  state,tail=queue.popleft()
  if all(v is None or v==current[i] for i,v in enumerate(state)):return list(reversed(tail))
  if len(tail)>=10:continue
  choices=[]
  for d,mask in ms.items():
   colors={state[i] for i in mask if state[i] is not None}
   if len(colors)!=1:continue
   color=next(iter(colors));nxt=list(state);removed=sum(state[i] is not None for i in mask)
   for i in mask:nxt[i]=None
   nxt=tuple(nxt)
   if nxt not in seen:choices.append((-removed,d,color,nxt))
  for _,d,color,nxt in sorted(choices):seen.add(nxt);queue.append((nxt,tail+[(d,color)]))
 return None
class Agent:
 def __init__(self):self.prior=Prior();self.edges={};self.pending=None;self.paint_evidence=[];self.refuted=[];self.steps=0;self.level=None;self.small_masks={};self.small_evidence=[];self.has_small=False;self.small_absent=set()
 def respond(self,obs):
  if self.pending:
   p=self.pending;e=dict(before=p['before'],action=p['action'],data=p['data'],after=copy.deepcopy(obs));source=digest(e)
   if obs['levels_completed']==p['before']['levels_completed']:
    ps=parts(obs['frame']);tools=[q for q in ps if q['y']>=16 and ((q['h'],q['w'],q['area']) in [(9,14,30),(14,9,30),(17,17,43)])]
    if p.get('mode')=='small':
     b=p['canvas'];before=[v for row in p['before']['frame'][b['y']:b['y']+b['h']] for v in row[b['x']:b['x']+b['w']]];actual=[v for row in obs['frame'][b['y']:b['y']+b['h']] for v in row[b['x']:b['x']+b['w']]]
     if p['color'] not in before:
      mask=tuple(i for i,v in enumerate(actual) if v==p['color']);self.small_masks[tuple(p['direction'])]=mask;self.small_evidence.append(dict(source=source,canvas=b,direction=p['direction'],color=p['color'],mask=mask))
    if p['action'] in (1,2,3,4) and len(tools)==1:self.edges.setdefault(tuple(p['direction']),{})[p['action']]=dict(direction=orient(tools[0],p['canvas']),source=source)
    if p['action']==5:
     b=p['canvas'];actual=[v for row in obs['frame'][b['y']:b['y']+b['h']] for v in row[b['x']:b['x']+b['w']]];match=actual==p['prediction'];self.paint_evidence.append(dict(source=source,direction=p['direction'],color=p['color'],prediction=p['prediction'],matched=match,progress=False))
     if not match:self.refuted.append(dict(source=source,direction=p['direction']))
   elif p['action']==5:self.paint_evidence.append(dict(source=source,direction=p['direction'],color=p['color'],prediction=p['prediction'],matched=None,progress=True))
   self.pending=None
  r=self.prior.respond(obs);g=self.prior.goal;b=self.prior.canvas
  if not g or not b or obs['state']!='NOT_FINISHED':return r
  if self.level!=obs['levels_completed']:self.level=obs['levels_completed'];self.steps=0
  ps=parts(obs['frame']);tools=[q for q in ps if q['y']>=16 and ((q['h'],q['w'],q['area']) in [(9,14,30),(14,9,30),(17,17,43)])]
  if len(tools)!=1 or self.steps>=160:return dict(action=None,data={},done=True,certificate=None,advisor='stencil_composition',diagnostics=dict(reason='unsupported_stencil_geometry'))
  tool=tools[0];direction=orient(tool,b);current=[v for row in obs['frame'][b['y']:b['y']+b['h']] for v in row[b['x']:b['x']+b['w']]];target=[v for row in g['image'] for v in row];all_masks={(0,)+d:v for d,v in masks(g['h'],g['w']).items()};all_masks.update({(1,)+d:v for d,v in self.small_masks.items()});plan=compose(current,target,g['h'],g['w'],all_masks);action=None;data={};reason='no_composed_paint_plan';prediction=None;color=None;mode=None;small=[q for q in ps if q['color']==tool['color'] and q['y']>=16 and 8<=q['area']<30 and q['h']>=4 and q['w']>=4];probe=False
  if small:self.has_small=True
  elif self.has_small:self.small_absent.add(direction)
  if not plan and self.has_small:
   if direction not in self.small_masks and small:
    colors=sorted({q['color'] for q in ps if q['y']<8 and q['x']>=16 and q['h']==q['w']==3 and q['area']==9}-set(current))
    if colors:plan=[((1,)+direction,colors[0])];probe=True
   else:
    missing=[d for d in DIRECTIONS if d not in self.small_masks and d not in self.small_absent]
    if missing:plan=[((1,)+missing[0],next(iter(set(target))))];probe=True
  if plan and not self.refuted:
   spec,color=plan[0];wanted=tuple(spec[1:]);mode='small' if spec[0] else 'large';buttons=[q for q in ps if q['color']==color and q['y']<8 and q['x']>=16 and q['h']==q['w']==3 and q['area']==9]
   selected=any(all(obs['frame'][q['y']+4][x]==0 for x in range(q['x']-1,q['x']+4)) for q in buttons)
   if buttons and not selected:q=buttons[0];action=6;data=dict(y=q['y']+1,x=q['x']+1);reason='select_color_for_composed_paint_operation'
   elif direction==wanted:
    if mode=='small' and small:
     q=small[0];action=6;data=dict(y=q['y']+q['h']//2,x=q['x']+q['w']//2);reason='test_secondary_tool_mask' if probe else 'apply_observed_secondary_tool_mask'
    elif mode=='large':action=5;reason='test_composed_paint_prediction'
    if spec in all_masks:
     prediction=current[:]
     for i in all_masks[spec]:prediction[i]=color
   else:
    queue=deque([(direction,[])]);seen={direction};route=None
    while queue:
     node,path=queue.popleft()
     if node==wanted:route=path;break
     for a,q in sorted(self.edges.get(node,{}).items()):
      nxt=tuple(q['direction'])
      if nxt not in seen:seen.add(nxt);queue.append((nxt,path+[a]))
    if route:action=route[0];reason='reuse_observed_tool_route'
    else:
     missing=[a for a in (1,2,3,4) if a not in self.edges.get(direction,{})]
     if missing:action=missing[0];reason='test_unobserved_tool_transition'
     else:
      queue=deque([(direction,[])]);seen={direction}
      while queue:
       node,path=queue.popleft()
       if len(self.edges.get(node,{}))<4 and path:action=path[0];reason='route_to_unexplored_tool_transition';break
       for a,q in sorted(self.edges.get(node,{}).items()):
        nxt=tuple(q['direction'])
        if nxt not in seen:seen.add(nxt);queue.append((nxt,path+[a]))
  c=None
  if action is not None:
   self.steps+=1;c=dict(kind='stencil_composition_hypothesis',context=digest(obs),action=action,goal=g,canvas=b,source=self.prior.source,tool=tool,direction=direction,plan=plan,prediction=prediction,color=color,controls=copy.deepcopy(self.edges),paint_evidence=copy.deepcopy(self.paint_evidence),goal_is_hypothesis=True,effects=copy.deepcopy(self.prior.effects))
   # JSON object keys must be strings; records preserve directional identities.
   c['small_evidence']=copy.deepcopy(self.small_evidence);c['small_tool']=small[0] if small else None;c['mode']=mode;c['probe']=probe
   c['controls']=[dict(origin=list(k),action=a,**q) for k,v in self.edges.items() for a,q in v.items()]
   self.pending=dict(before=copy.deepcopy(obs),action=action,data=data,canvas=copy.deepcopy(b),direction=direction,color=color,prediction=prediction,mode=mode if action==5 or (action==6 and data.get('y',0)>=16) else None)
  out=dict(action=action,data=data,done=action is None,certificate=c,advisor='stencil_composition',diagnostics=dict(reason=reason,steps=self.steps,refutations=len(self.refuted)));self.prior.last=copy.deepcopy(out);self.prior.pending_tool=None;return out
