"""Infer a small visible target and test rotating-tool alignment before painting."""
import copy,math
from collections import Counter
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.level=None;self.goal=None;self.canvas=None;self.source=None;self.paint=None;self.selected=False;self.steps=0;self.previous=None;self.last=None;self.effects=[];self.tool_edges={};self.pending_tool=None
 def respond(self,obs):
  ps=parts(obs['frame']);f=obs['frame'];a=None;data={};c=None;reason='unresolved_stencil_scene'
  if self.previous is not None:
   e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));self.effects.append(dict(source=digest(e),progress=obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN'))
  if self.level!=obs['levels_completed']:
   self.level=obs['levels_completed'];self.goal=None;self.canvas=None;self.selected=False;self.steps=0;pieces=[p for p in ps if p['x']<16 and p['y']<16 and p['area']>=9];palette={p['color'] for p in pieces}
   if len(pieces)>=2:
    y=min(p['y'] for p in pieces);x=min(p['x'] for p in pieces);h=max(p['y']+p['h'] for p in pieces)-y;ww=max(p['x']+p['w'] for p in pieces)-x;image=[row[x:x+ww] for row in f[y:y+h]];candidates=[p for p in ps if p['y']>=16 and p['h']==h and p['w']==ww and p['area']>=.8*h*ww]
    if len(candidates)==1:self.goal=dict(y=y,x=x,h=h,w=ww,image=image);self.canvas={k:candidates[0][k] for k in ['y','x','h','w','color']};self.source=digest(obs);wanted=Counter(v for row in image for v in row if v!=self.canvas['color']);self.paint=wanted.most_common(1)[0][0] if wanted else None
  tool=None;desired=None;alignment=None
  if self.goal and self.canvas and self.paint is not None and obs['state']=='NOT_FINISHED' and self.steps<64:
   g,b=self.goal,self.canvas;buttons=[p for p in ps if p['color']==self.paint and p['y']<8 and p['x']>=16 and p['h']==p['w']==3 and p['area']==9]
   if not self.selected and buttons:p=buttons[0];a=6;data=dict(y=p['y']+1,x=p['x']+1);self.selected=True;reason='test_palette_selection_from_target_color'
   else:
    palette={v for row in g['image'] for v in row};tools=[p for p in ps if p['color'] not in palette and p['y']>=16 and 20<=p['area']<=150 and p['h']<=30 and p['w']<=30]
    if len(tools)==1:
     tool=tools[0];points=[(tool['y']+y,tool['x']+x) for y,x in tool['shape']];center=(b['y']+(b['h']-1)/2,b['x']+(b['w']-1)/2);direction=tuple(sum(p[i] for p in points)/len(points)-center[i] for i in (0,1));wanted=[(y,x) for y,row in enumerate(g['image']) for x,v in enumerate(row) if v==self.paint];desired=tuple(sum(p[i] for p in wanted)/len(wanted)-(g['h' if i==0 else 'w']-1)/2 for i in (0,1));scale=math.hypot(*direction)*math.hypot(*desired);alignment=sum(direction[i]*desired[i] for i in (0,1))/scale if scale else None
     if alignment is not None and alignment>.97:a=5;reason='test_tool_mask_aligned_with_target_color_region'
     elif alignment is not None:
      key=digest(tool)
      if self.pending_tool is not None:
       old,control=self.pending_tool;self.tool_edges.setdefault(old,{})[control]=key;self.pending_tool=None
      tested=self.tool_edges.setdefault(key,{})
      missing=[z for z in (4,2,1,3) if z in obs['available_actions'] and z not in tested]
      if missing:a=missing[0];reason='test_unobserved_tool_control'
      else:
       queue=[(key,[])];seen={key}
       for node,path in queue:
        if node!=key and len(self.tool_edges.get(node,{}))<4:a=path[0];reason='return_to_tool_state_with_untried_control';break
        for action,nxt in self.tool_edges.get(node,{}).items():
         if nxt not in seen:seen.add(nxt);queue.append((nxt,path+[action]))
      if a is not None:self.pending_tool=(key,a)
   if a is not None:c=dict(kind='stencil_goal_hypothesis',context=digest(obs),action=a,goal=self.goal,canvas=self.canvas,source=self.source,paint_color=self.paint,tool=tool,target_direction=desired,alignment=alignment,effects=copy.deepcopy(self.effects),goal_is_hypothesis=True);self.steps+=1
  r=dict(action=a,data=data,done=a is None,certificate=c,advisor='stencil_goal_inquiry',diagnostics=dict(reason=reason,steps=self.steps));self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r);return r
