"""Bounded legal-pixel interaction inquiry for unlabeled linked-object groups."""
import copy,itertools
from collections import Counter
from group_centroid_learner_v14 import Agent as Prior,blocked,route
from group_symbolic_scene_v1 import DISK,RING
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
BODY=DISK+[(0,0)]
def parse(obs):
    f=obs['frame'];bg=Counter(v for row in f for v in row).most_common(1)[0][0];ends=[];pads=[];groups=[]
    for q in parts(f):
        if q['h']==q['w']==5 and q['area']==12:ends.append(dict(color=q['color'],point=(q['y']+2,q['x']+2)))
    for y in range(2,62):
        for x in range(2,62):
            vals={f[y+a][x+b] for a,b in BODY}
            if len(vals)==2 and 0 in vals and bg not in vals and all(f[y+a][x+b]==bg for a,b in [(-2,-2),(-2,2),(2,-2),(2,2)]):pads.append(dict(center=(y,x),signature=sorted(vals)))
    for n in range(2,min(6,len(ends))+1):
        for subset in itertools.combinations(ends,n):
            center=tuple(sum(o['point'][i] for o in subset)//n for i in (0,1));y,x=center
            vals={f[y+a][x+b] for a,b in BODY}
            if bg not in vals and len(vals)<=4:groups.append(dict(members=list(subset),center=center,signature=sorted(vals)))
    return ends,pads,groups
class Agent:
    def __init__(self):self.prior=Prior();self.exploring=False;self.steps=0;self.previous=None;self.last=None;self.outcomes=[];self.visited=set();self.target=None;self.retreating=False;self.contact_site=None
    def respond(self,obs):
        if not self.exploring:
            candidate=self.prior.respond(obs)
            if not candidate['done'] or obs['state']!='NOT_FINISHED':return candidate
            ends,pads,groups=parse(obs)
            if not pads or not groups:return candidate
            self.exploring=True
        if self.previous is not None:
            e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));self.outcomes.append(dict(source=digest(e),before_level=self.previous['levels_completed'],after_level=obs['levels_completed'],progress=obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN'))
        ends,pads,groups=parse(obs);active_color=self.prior.active_color;active=next((o for o in ends if o['color']==active_color),None);group=next((g for g in sorted(groups,key=lambda g:len(g['members'])) if active in g['members']),None);action=None;data={};cert=None
        if self.steps<24 and group and obs['state']=='NOT_FINISHED':
            if self.target and max(abs(group['center'][i]-self.target['center'][i]) for i in (0,1))<=1:
                if self.retreating:self.visited.add(tuple(self.contact_site['center']));self.retreating=False;self.contact_site=None;self.target=None
                else:
                    self.contact_site=copy.deepcopy(self.target);bad=blocked(obs,[]);n=len(group['members']);candidates=[]
                    for dy in range(-9,10):
                        for dx in range(-9,10):
                            q=(group['center'][0]+dy,group['center'][1]+dx)
                            if not(3<=q[0]<61 and 3<=q[1]<61) or q in bad or not(6<=abs(dy)+abs(dx)<=9):continue
                            if any(max(abs(q[i]-pad['center'][i]) for i in (0,1))<=5 for pad in pads):continue
                            for member in group['members']:
                                dest=tuple(n*q[i]-sum(o['point'][i] for o in group['members'] if o is not member) for i in (0,1))
                                if not(3<=dest[0]<61 and 3<=dest[1]<61) or dest in bad:continue
                                if any(max(abs(dest[i]-o['point'][i]) for i in (0,1))<5 for o in ends if o is not member):continue
                                candidates.append((member is not active,abs(dy)+abs(dx),q))
                    if candidates:self.target=dict(center=min(candidates)[2],signature=[],interpretation='leave_site_to_test_persistent_change');self.retreating=True
                    else:self.visited.add(tuple(self.target['center']));self.target=None
            options=[p for p in pads if tuple(p['center']) not in self.visited]
            if self.target is None and options:self.target=min(options,key=lambda p:(sum(abs(p['center'][i]-group['center'][i]) for i in (0,1)),p['center']))
            if self.target:
                bad=blocked(obs,[]);path=route(group['center'],self.target['center'],bad);choices=[];n=len(group['members'])
                for j,q in enumerate(path or []):
                    if j==0:continue
                    for member in group['members']:
                        for rem in itertools.product(range(n),repeat=2):
                            p=tuple(n*q[i]-sum(o['point'][i] for o in group['members'] if o is not member)+rem[i] for i in (0,1))
                            if not(3<=p[0]<61 and 3<=p[1]<61) or p in bad:continue
                            if max(abs(p[i]-member['point'][i]) for i in (0,1))<3:continue
                            if any(max(abs(p[i]-o['point'][i]) for i in (0,1))<5 for o in ends if o is not member):continue
                            choices.append((j,member is active,-sum(abs(p[i]-member['point'][i]) for i in (0,1)),member['point'],p,q))
                if choices:
                    _,_,_,origin,dest,next_center=max(choices);p=dest if origin==active['point'] else origin;action=6;data=dict(y=p[0],x=p[1]);cert=dict(kind='anonymous_link_interaction_probe',context=digest(obs),action=6,click=p,group=group,target=copy.deepcopy(self.target),origin=origin,destination=dest,predicted_center=next_center,selection_probe=origin!=active['point'],goal_is_hypothesis=True,retreating=self.retreating,contact_site=copy.deepcopy(self.contact_site),retained_outcomes=copy.deepcopy(self.outcomes));self.steps+=1
        response=dict(action=action,data=data,done=action is None,certificate=cert,advisor='anonymous_link_inquiry',diagnostics=dict(reason='bounded_interaction_probe' if action else 'bounded_inquiry_stopped',probes=self.steps,outcomes=copy.deepcopy(self.outcomes)))
        self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(response);return response
