"""Retain observed board geometry across camera motion and compose learned jump rules."""
import copy
from coupled_peg_inquiry_v3 import Agent as Prefix
from typed_peg_planning_v2 import search,configs,shift,regions
from peg_world_memory_v13 import Memory
class Agent:
    def __init__(self,prior=None):
        self.prior=prior;self.prefix=Prefix();self.memory=Memory();self.active=True;self.own=False;self.t=0;self.controls={};self.rules=[];self.selected=None;self.previous=None;self.outcomes=[];self.tried_frontiers=set();self.retained_plan=None;self.camera_actions=[];self.visibility_recoveries=[]
    def respond(self,raw):
        if not self.own:
            r=self.prefix.respond(raw);self.t=self.prefix.t
            if r.get('certificate',{}).get('kind')=='coupled_peg_inquiry':self.memory.observe(raw,r['certificate']['source'])
            if not r['done']or raw['state']!='NOT_FINISHED'or not self.prefix.L:return r
            self.own=True;self.controls=copy.deepcopy(self.prefix.controls);self.rules=copy.deepcopy(self.prefix.rule_memory)
        if raw['state']!='NOT_FINISHED'or self.t>=512:return dict(done=True,action=None,data={})
        v=self.memory.observe(raw,self.t)
        if not v:
            p=self.previous
            if p and p['source']>=self.memory.origin and p['action']in(1,2,3,4)and p['source']not in self.visibility_recoveries:
                delta=next((d for d,a in self.controls.items()if a==p['action']),None);inverse=next((a for d,a in self.controls.items()if delta and d==tuple(-x for x in delta)),None)
                size=self.memory.layout['scene']['size']if self.memory.layout else 4;camera=self.memory.camera
                if inverse and any(any(q[j]+delta[j]-camera[j]<0 or q[j]+delta[j]-camera[j]+size>64 for j in(0,1))for q in p['positions']):
                    c=dict(kind='carrier_visibility_recovery',source=self.t,support=p['source'],inverse_of=p['action'],controls=[dict(delta=d,action=a)for d,a in sorted(self.controls.items())],hypothesis='reverse_last_witnessed_control_after_a_carrier_leaves_the_visible_edge')
                    self.visibility_recoveries.append(p['source']);self.previous=None;self.t+=1;return dict(done=False,action=inverse,data={},certificate=c)
            return dict(done=True,action=None,data={})
        L=v['layout'];pos=v['positions'];marks=v['marks'];camera=v['camera'];s=L['scene'];k=(s['size']-1)//2
        if self.previous:
            p=self.previous
            for event in self.memory.camera_events:
                if event['source']==p['source'] and p['action']in(1,2,3,4):self.camera_actions.append(dict(source=p['source'],action=p['action'],delta=event['delta'],level=self.memory.level))
            self.outcomes.append(dict(source=p['source'],action=p['action'],before=p['positions'],after=pos,marks_before=p['marks'],marks_after=sorted(marks),level=raw['levels_completed']));self.previous=None
        def point(p):return dict(x=p[1]-camera[1]+k,y=p[0]-camera[0]+k)
        def visible(p):return 0<=p[0]-camera[0]<=64-s['size']and 0<=p[1]-camera[1]<=64-s['size']
        action=None;data={};extra={};tag='';mapkey=(tuple(L['rails']),tuple(s['cells']),tuple(L.get('pivots',[])))
        if self.selected:
            jump=self.selected;self.selected=None;self.retained_plan=None
            if visible(jump[2]):action=6;data=point(jump[2]);tag='land_retained_world_jump';extra['jump']=jump
        else:
            region=None;target_count=1;cached=self.retained_plan
            if cached and cached['positions']==pos and cached['marks']==marks and cached['mapkey']==mapkey:plan=cached['plan'];nodes=0;region=cached.get('region');target_count=cached.get('target_count',1)
            else:
                plan,nodes=search(L,pos,marks,limit=30000)
                if plan is None:
                    for area in regions(L):
                        if len(area&marks)<2:continue
                        candidate,count=search(L,pos,marks,limit=30000,goal_region=area);nodes+=count
                        if candidate:plan=candidate;region=sorted(area);break
            if plan:
                first=plan[0];extra=dict(joint_plan=copy.deepcopy(plan),search_nodes=nodes,partial_goal_region=region,partial_goal_count=target_count)
                if first['steps']:
                    delta=tuple(first['steps'][0]);action=self.controls.get(delta);tag='move_carriers_in_retained_world'
                    nxt,m=shift(pos,marks,delta,set(L['rails']));remaining=copy.deepcopy(plan);remaining[0]['steps']=remaining[0]['steps'][1:];self.retained_plan=dict(positions=nxt,marks=m,mapkey=mapkey,plan=remaining,region=region,target_count=target_count)
                elif visible(first['jump'][0])and visible(first['jump'][2]):
                    self.selected=first['jump'];action=6;data=point(first['jump'][0]);tag='select_retained_world_jump'
                else:
                    target=next(p for p in(first['jump'][0],first['jump'][2])if not visible(p));choices=[]
                    for dest,path in configs(L,pos).items():
                        if not path:continue
                        q=pos;m=marks
                        for d in path:q,m=shift(q,m,d,set(L['rails']))
                        loaded=set(q)&m
                        if loaded:choices.append((min(sum(abs(p[j]-target[j])for j in(0,1))for p in loaded),len(path),path))
                    if choices:
                        _,_,path=min(choices);action=self.controls.get(tuple(path[0]));tag='bring_remembered_jump_into_view';extra=dict(view_target=target,view_path=path)
            if action is None:
                for learned in reversed(self.camera_actions):
                    if learned['level']!=self.memory.level:continue
                    delta=next((d for d,a in self.controls.items()if a==learned['action']),None)
                    if delta is None or not any(p in marks and (p[0]+delta[0],p[1]+delta[1])in set(L['rails'])for p in pos):continue
                    dy,dx=learned['delta'];edge=any((dx>0 and p[1]-camera[1]+s['size']>=64-s['pitch'])or(dx<0 and p[1]-camera[1]<s['pitch'])or(dy>0 and p[0]-camera[0]+s['size']>=64-s['pitch'])or(dy<0 and p[0]-camera[0]<s['pitch'])for p in s['cells']if visible(p))
                    if edge:action=learned['action'];tag='explore_using_observed_camera_motion';extra=dict(camera_motion_hypothesis=copy.deepcopy(learned));break
            if action is None:
                choices=[]
                for dest,path in configs(L,pos).items():
                    for p in dest:
                        for d,a in sorted(self.controls.items()):
                            q=(p[0]+d[0],p[1]+d[1]);key=(self.memory.level,p,d)
                            if q not in set(L['rails'])|set(s['cells'])and not visible(q)and key not in self.tried_frontiers:choices.append((len(path),dest,p,d,a,path,key))
                if choices:
                    _,dest,p,d,a,path,key=min(choices);action=self.controls.get(tuple(path[0]))if path else a;tag='explore_retained_rail_frontier';extra=dict(frontier=dict(carrier_at=p,unknown_neighbor=(p[0]+d[0],p[1]+d[1]),direction=d,path=path))
                    if not path:self.tried_frontiers.add(key)
        if action is None:return dict(done=True,action=None,data={})
        c=dict(kind='viewport_peg_learning',source=self.t,tag=tag,layout=copy.deepcopy(L),positions=pos,marks=sorted(marks),carriers=v['carriers'],world_memory=self.memory.certificate(),controls=[dict(delta=d,action=a)for d,a in sorted(self.controls.items())],rule_memory=copy.deepcopy(self.rules),outcomes=copy.deepcopy(self.outcomes),goal_is_hypothesis=True,**extra)
        self.previous=dict(source=self.t,action=action,positions=pos,marks=sorted(marks));self.t+=1
        return dict(done=False,action=action,data=data,certificate=c)
