import copy
from nested_sequence_model_v3 import scene,synthesize,center,ring_color
class Agent:
 def __init__(self):self.active=True;self.level=None;self.context=None;self.plan=None;self.pending=None;self.previous=None;self.t=0;self.history=[];self.failed=set();self.selected=None;self.submitted=set()
 def answer(self,o,point,phase,item,tool=None):
  x,y=point;c=dict(kind='nested_sequence',source=self.t,scene_source=self.scene_source,scene=copy.deepcopy(self.context),plan=copy.deepcopy(self.plan),phase=phase,item=copy.deepcopy(item),point=point,tool=copy.deepcopy(tool),memory=copy.deepcopy(self.history))
  r=dict(done=False,action=6,data=dict(x=x,y=y),certificate=c,advisor='nested_sequence_inquiry');self.previous=dict(o=copy.deepcopy(o),r=copy.deepcopy(r),source=self.t);self.t+=1;return r
 def respond(self,o):
  if self.previous:
   p=self.previous;r=p['r'];x,y=(r['data']['x'],r['data']['y'])if r['action']==6 else (0,0);claim=dict(source=p['source'],action=r['action'],point=(x,y),before=p['o']['frame'][y][x],after=o['frame'][y][x],progress=o['levels_completed']>p['o']['levels_completed']or o['state']=='WIN')
   self.history.append(claim);self.previous=None
   if r['certificate']['phase']=='apply':
    it=r['certificate']['item'];t=self.context['groups'][it['group']]['tokens'][it['slot']];hit=ring_color(o['frame'],t)==it['ink']if it['kind']=='reference'else o['frame'][y][x]==it['ink']
    if not hit and not claim['progress']:self.failed.add((self.level,it['group'],it['slot'],it['kind'],it['ink']))
  if o['state']=='WIN':return dict(done=True,action=None,data={})
  if o['state']!='NOT_FINISHED':return dict(done=True,action=None,data={})
  if self.level!=o['levels_completed']:
   self.level=o['levels_completed'];self.context=scene(o);self.scene_source=self.t;self.plan=synthesize(self.context)if self.context else None;self.pending=None;self.selected=None
  if not self.plan:return dict(done=True,action=None,data={})
  if self.pending:
   it,tool=self.pending;self.pending=None;t=self.context['groups'][it['group']]['tokens'][it['slot']];return self.answer(o,center(t),'apply',it,tool)
  for it in self.plan['assignments']:
   t=self.context['groups'][it['group']]['tokens'][it['slot']];x,y=center(t)
   fulfilled=ring_color(o['frame'],t)==it['ink']if it['kind']=='reference'else o['frame'][y][x]==it['ink']and ring_color(o['frame'],t)is None
   if fulfilled:continue
   if (self.level,it['group'],it['slot'],it['kind'],it['ink'])in self.failed:return dict(done=True,action=None,data={})
   tools=[p for p in self.context['palette']if p['color']==it['ink']and p['hollow']==(it['kind']=='reference')and(ring_color(o['frame'],p)==it['ink']if p['hollow']else o['frame'][center(p)[1]][center(p)[0]]==it['ink'])]
   if not tools:return dict(done=True,action=None,data={})
   tool=tools[0];self.pending=(copy.deepcopy(it),copy.deepcopy(tool));return self.answer(o,center(tool),'select',it,tool)
  options=[a for a in o['available_actions']if a not in (0,6)and(self.level,a)not in self.submitted]
  if options:
   evidence=[]if getattr(self,'erase_submission_retrieval',False)else[m for m in self.history if m['progress']and m['action']!=6 and m['action']in options];a=evidence[-1]['action']if evidence else min(options);self.submitted.add((self.level,a));c=dict(kind='nested_sequence',source=self.t,scene_source=self.scene_source,scene=copy.deepcopy(self.context),plan=copy.deepcopy(self.plan),phase='submit_hypothesis',point=None,submission_memory=copy.deepcopy(evidence),memory=copy.deepcopy(self.history));r=dict(done=False,action=a,data={},certificate=c,advisor='nested_sequence_inquiry');self.previous=dict(o=copy.deepcopy(o),r=copy.deepcopy(r),source=self.t);self.t+=1;return r
  return dict(done=True,action=None,data={})
