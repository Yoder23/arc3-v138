"""Learn click-to-endpoint effects and test collinear visible endpoint goals."""
import copy
from collections import Counter
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
def scene(obs):
 f=obs['frame'];ps=parts(f);background=Counter(v for row in f for v in row).most_common(1)[0][0];bars=[];goals=[]
 for p in ps:
  if (p['h']==3 and p['w']>=2 or p['w']==3 and p['h']>=2) and p['area']>=5:
   holes=[(y,x,f[y][x]) for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w']) if f[y][x]!=p['color']]
   if len(holes)==1:
    y,x,color=holes[0];axis=1 if p['h']==3 else 0;buttons=[q for q in ps if q['color']==p['color'] and q['h']==q['w']==3 and q['area']==7];bars.append(dict(color=p['color'],marker=color,endpoint=[y,x],axis=axis,body=p,buttons=buttons))
 for bar in bars:
  c=bar['marker']
  for y in range(1,61):
   for x in range(1,63):
    if f[y][x]==background and all(f[y+dy][x+dx]==c for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]):
     q=[y,x]
     if q not in goals:goals.append(q)
 return bars,goals
class Agent:
 def __init__(self):self.previous=None;self.last=None;self.pending=None;self.models={};self.effects=[];self.steps=0;self.level=None
 def respond(self,obs):
  bars,goals=scene(obs)
  if self.previous is not None:
   e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));source=digest(e);self.effects.append(dict(source=source,progress=obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN'))
   if self.pending and self.previous['levels_completed']==obs['levels_completed']:
    old,button=self.pending;matches=[b for b in bars if b['color']==old['color']]
    if len(matches)==1:
     new=matches[0];delta=[new['endpoint'][i]-old['endpoint'][i] for i in (0,1)];self.models[(old['color'],tuple(map(tuple,button['shape'])))]=dict(delta=delta,source=source,before=old,after=new,button=button)
  self.pending=None
  if self.level!=obs['levels_completed']:self.level=obs['levels_completed'];self.steps=0
  a=None;data={};c=None;reason='unresolved_endpoint_goal'
  if obs['state']=='NOT_FINISHED' and self.steps<180:
   for bar in bars:
    axis=bar['axis'];matched=[g for g in goals if g[1-axis]==bar['endpoint'][1-axis] and g!=bar['endpoint']]
    if len(matched)!=1:continue
    goal=matched[0];distance=goal[axis]-bar['endpoint'][axis];button=None
    for q in bar['buttons']:
     m=self.models.get((bar['color'],tuple(map(tuple,q['shape']))))
     if m and m['delta'][1-axis]==0 and m['delta'][axis]*distance>0 and abs(m['delta'][axis])<=abs(distance):button=q;reason='reuse_observed_endpoint_motion_toward_goal';break
    if button is None:
     for q in bar['buttons']:
      if (bar['color'],tuple(map(tuple,q['shape']))) not in self.models:button=q;reason='test_click_to_endpoint_effect';break
    if button:
     a=6;data=dict(y=button['y']+1,x=button['x']+1);self.pending=(copy.deepcopy(bar),copy.deepcopy(button));c=dict(kind='endpoint_goal_hypothesis',context=digest(obs),action=a,bar=bar,button=button,goal=goal,goals=goals,models=list(copy.deepcopy(self.models).values()),effects=copy.deepcopy(self.effects),goal_is_hypothesis=True);self.steps+=1;break
  r=dict(action=a,data=data,done=a is None,certificate=c,advisor='endpoint_extension_inquiry',diagnostics=dict(reason=reason,steps=self.steps));self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r);return r
