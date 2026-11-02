"""Test repeated binary commands using only observed switch values and a submit glyph."""
import copy
from collections import Counter

def components(frame):
 seen=set();out=[]
 for y in range(len(frame)):
  for x in range(len(frame[0])):
   if (y,x)in seen:continue
   ink=frame[y][x];seen.add((y,x));todo=[(y,x)];pts=[]
   while todo:
    p=todo.pop();pts.append(p)
    for q in((p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)):
     if 0<=q[0]<len(frame)and 0<=q[1]<len(frame[0])and q not in seen and frame[q[0]][q[1]]==ink:seen.add(q);todo.append(q)
   yy=min(p[0]for p in pts);xx=min(p[1]for p in pts);h=max(p[0]for p in pts)-yy+1;ww=max(p[1]for p in pts)-xx+1
   out.append(dict(ink=ink,box=(yy,xx,h,ww),shape=sorted((a-yy,b-xx)for a,b in pts)))
 return out
class Agent:
 def __init__(self,prior=None):self.prior=prior;self.active=True;self.t=0;self.level=None;self.rows=None;self.button=None;self.test=0;self.memory=[];self.previous=None;self.after_submit=False;self.failures=Counter()
 def respond(self,raw):
  if self.previous:self.memory.append(dict(source=self.previous['source'],action=6,data=self.previous['data'],before_ink=self.previous['raw']['frame'][self.previous['data']['y']][self.previous['data']['x']],after_ink=raw['frame'][self.previous['data']['y']][self.previous['data']['x']],before_level=self.previous['raw']['levels_completed'],after_level=raw['levels_completed']))
  if raw['state']!='NOT_FINISHED':return dict(done=True,action=None,data={})
  if self.level!=raw['levels_completed']:
   if self.level is not None:return dict(done=True,action=None,data={})
   self.level=raw['levels_completed'];obs=components(raw['frame']);h=[o for o in obs if o['box'][2:]==(1,3)];v=[o for o in obs if o['box'][2:]==(3,1)];pairs=[(a,b)for a in h for b in v if a['box'][1]+1==b['box'][1] and b['box'][0]==a['box'][0]+2]
   if len(pairs)<3:return dict(done=True,action=None,data={})
   line=Counter(a['box'][0]for a,b in pairs).most_common(1)[0][0];pairs=sorted([p for p in pairs if p[0]['box'][0]==line],key=lambda p:p[0]['box'][1]);self.rows=[[p[j]for p in pairs]for j in(0,1)];self.values=sorted({o['ink']for row in self.rows for o in row});buttons=[o for o in obs if 5<=min(o['box'][2:])<=max(o['box'][2:])<=12 and o['box'][0]>line+4 and len(o['shape'])>25]
   if len(self.values)!=2 or not buttons:return dict(done=True,action=None,data={})
   self.button=max(buttons,key=lambda o:len(o['shape']));self.initial=copy.deepcopy(self.rows);self.initial_source=self.t
  if self.after_submit:self.test+=1;self.after_submit=False
  if self.test>=4:return dict(done=True,action=None,data={})
  desired=[self.values[(self.test>>j)&1]for j in(0,1)];data=None;tag=''
  for j,row in enumerate(self.rows):
   for o in row:
    y,x,h,w=o['box'];yy=y+(h-1)//2;xx=x+(w-1)//2
    if raw['frame'][yy][xx]!=desired[j]:data=dict(x=xx,y=yy);tag='set_binary_command';break
   if data:break
  if data is None:
   y,x,h,w=self.button['box'];data=dict(x=x+(w-1)//2,y=y+(h-1)//2);tag='test_repeated_command';self.after_submit=True
  key=(self.test,data['x'],data['y']);self.failures[key]+=1
  if self.failures[key]>3:return dict(done=True,action=None,data={})
  c=dict(kind='binary_command_inquiry',source=self.t,initial_source=self.initial_source,rows=self.initial,button=self.button,test=self.test,desired=desired,memory=copy.deepcopy(self.memory),tag=tag,goal_is_hypothesis=True);self.previous=dict(source=self.t,raw=copy.deepcopy(raw),data=data);self.t+=1;return dict(done=False,action=6,data=data,certificate=c)
