import copy
from rail_peg_inquiry_v2 import Agent as Prefix
from coupled_peg_model_v3 import layout,carriers,search,shift,regions
class Agent:
 def __init__(self,prior=None):self.prior=prior;self.active=True;self.prefix=Prefix();self.L=None;self.level=None;self.t=0;self.previous=None;self.selected=None;self.outcomes=[];self.rule_memory=[];self.controls={};self.retained_plan=None
 def respond(self,raw):
  if self.L is None:
   candidate=layout(raw['frame']) if raw['levels_completed']!=self.prefix.level else None
   if candidate and len(candidate['carriers'])>1 and self.prefix.rule_memory:
    self.L=candidate;self.level=raw['levels_completed'];self.t=self.prefix.t;self.L['source']=self.t;self.rule_memory=copy.deepcopy(self.prefix.rule_memory);self.controls=copy.deepcopy(self.prefix.controls)
   else:return self.prefix.respond(raw)
  if raw['state']!='NOT_FINISHED':return dict(done=True,action=None,data={})
  if raw['levels_completed']!=self.level:
   self.L=layout(raw['frame']);self.level=raw['levels_completed'];self.previous=None;self.selected=None;self.retained_plan=None
   if not self.L:return dict(done=True,action=None,data={})
   self.L['source']=self.t
  known=self.previous['positions'] if self.previous and self.previous['action']==6 else ()
  bodies=carriers(raw['frame'],self.L['scene']['size'],self.L['carrier_ink'],known)
  if len(bodies)!=len(self.L['carriers']):return dict(done=True,action=None,data={})
  positions=tuple((o['box'][0]+1,o['box'][1]+1)for o in bodies);s=self.L['scene'];k=(s['size']-1)//2;marks=frozenset(tuple(p)for p in s['cells']+list(positions)if raw['frame'][p[0]+k][p[1]+k]==s['mark'])
  if self.previous:
   p=self.previous;self.outcomes.append(dict(source=p['source'],action=p['action'],before=p['positions'],after=positions,marks_before=p['marks'],marks_after=sorted(marks)))
  extra={};data={}
  if self.selected:
   a,b,c=self.selected;action=6;data=self.point(c);tag='test_coupled_jump_landing';extra['jump']=self.selected;self.selected=None;self.retained_plan=None
  else:
   if self.retained_plan and self.retained_plan['positions']==positions and self.retained_plan['marks']==marks:plan=self.retained_plan['plan'];n=0;region=self.retained_plan.get('region');target_count=self.retained_plan.get('target_count',1)
   else:
    plan,n=search(self.L,positions,marks);region=None;target_count=1
    if plan is None:
     for area in regions(self.L):
      if len(area & marks)<2:continue
      candidate,count=search(self.L,positions,marks,goal_region=area);n+=count
      if candidate:plan=candidate;region=sorted(area);break
    if plan is None:
     for count_goal in range(2,len(marks)):
      for area in regions(self.L):
       if len(area & marks)<=count_goal:continue
       candidate,count=search(self.L,positions,marks,goal_region=area,target_count=count_goal);n+=count
       if candidate:plan=candidate;region=sorted(area);target_count=count_goal;break
      if plan:break
   if not plan:return dict(done=True,action=None,data={})
   first=plan[0];extra=dict(joint_plan=copy.deepcopy(plan),search_nodes=n,partial_goal_region=region,partial_goal_count=target_count)
   if first['steps']:
    delta=tuple(first['steps'][0]);action=self.controls.get(delta);tag='move_coupled_carriers'
    if action is None:return dict(done=True,action=None,data={})
    nextpos,nextmarks=shift(positions,marks,delta,set(map(tuple,self.L['rails'])));remaining=copy.deepcopy(plan);remaining[0]['steps']=remaining[0]['steps'][1:];self.retained_plan=dict(positions=nextpos,marks=nextmarks,plan=remaining,region=region,target_count=target_count)
   else:action=6;self.selected=first['jump'];data=self.point(first['jump'][0]);tag='select_coupled_jump'
  c=dict(kind='coupled_peg_inquiry',source=self.t,layout=copy.deepcopy(self.L),carriers=bodies,positions=positions,marks=sorted(marks),rule_memory=copy.deepcopy(self.rule_memory),outcomes=copy.deepcopy(self.outcomes),controls=[dict(delta=d,action=a)for d,a in sorted(self.controls.items())],tag=tag,goal_is_hypothesis=True,**extra)
  self.previous=dict(source=self.t,action=action,positions=positions,marks=sorted(marks));self.t+=1;return dict(done=False,action=action,data=data,certificate=c)
 def point(self,p):k=(self.L['scene']['size']-1)//2;return dict(x=p[1]+k,y=p[0]+k)
