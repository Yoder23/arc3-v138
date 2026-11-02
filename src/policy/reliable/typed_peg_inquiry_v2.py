"""Test the retained jump relation across a new visible intermediate token."""
import copy
from collections import Counter
from viewport_peg_learning_v5 import Agent as Prefix
class Agent:
    def __init__(self,prior=None):self.prior=prior;self.prefix=Prefix();self.active=True;self.t=0;self.inquiry=None;self.selected=None;self.complete=False;self.outcome=None
    def respond(self,raw):
        if self.inquiry is None:
            r=self.prefix.respond(raw);self.t=self.prefix.t
            if not r['done']or raw['state']!='NOT_FINISHED'or self.prefix.memory.layout is None:return r
            m=self.prefix.memory;L=m.layout;s=L['scene'];camera=m.camera;k=(s['size']-1)//2;pitch=s['pitch'];f=raw['frame'];bg=Counter(v for row in f for v in row).most_common(1)[0][0];cells=set(map(tuple,s['cells']));choices=[]
            for a in sorted(m.mark_support):
                for dy,dx in[(-pitch,0),(pitch,0),(0,-pitch),(0,pitch)]:
                    b=(a[0]+dy,a[1]+dx);z=(a[0]+2*dy,a[1]+2*dx);local=[(p[0]-camera[0],p[1]-camera[1])for p in[a,b,z]]
                    if not all(0<=y<=64-s['size']and 0<=x<=64-s['size']for y,x in local)or z not in cells or z in m.mark_support:continue
                    ink=f[local[1][0]+k][local[1][1]+k]
                    if ink in(s['field'],s['mark'],bg,L['track']):continue
                    neighbors=[(b[0]+yy,b[1]+xx)for yy,xx in[(-pitch,0),(pitch,0),(0,-pitch),(0,pitch)]]
                    if sum(p in cells for p in neighbors)<3:continue
                    choices.append((a,b,z,ink,local))
            if not choices:self.complete=True;self.inquiry={};return r
            a,b,z,ink,local=min(choices);self.inquiry=dict(source=self.t,level=raw['levels_completed'],jump=(a,b,z),local_jump=local,intermediate_ink=ink,field=s['field'],mark=s['mark'],size=s['size'],pitch=pitch,camera=camera,hypothesis='test_learned_jump_across_a_distinct_visible_token');self.selected=copy.deepcopy(raw)
            stage='select';target=local[0]
        elif self.complete:return dict(done=True,action=None,data={},certificate=dict(typed_jump_outcome=self.outcome))
        else:
            p=self.inquiry;z=p['local_jump'][2];f=raw['frame'];size=p['size'];before=self.selected['frame'];changed=[(y,x)for y in range(z[0],z[0]+size)for x in range(z[1],z[1]+size)if f[y][x]!=before[y][x]and f[y][x]not in(p['field'],p['mark'])]
            if not changed:self.complete=True;self.outcome=dict(selection_activated=False,source=p['source']);return dict(done=True,action=None,data={},certificate=dict(typed_jump_outcome=self.outcome))
            stage='land';target=z;self.complete=True;self.outcome=dict(selection_activated=True,source=p['source'],landing_source=self.t,landing_outcome_unchecked=True)
        k=(self.inquiry['size']-1)//2;data=dict(x=target[1]+k,y=target[0]+k);c=dict(kind='typed_peg_inquiry',source=self.t,stage=stage,inquiry=copy.deepcopy(self.inquiry),retained_rule_sources=[r['source']for r in self.prefix.rules],goal_is_hypothesis=True)
        self.t+=1;return dict(done=False,action=6,data=data,certificate=c)
