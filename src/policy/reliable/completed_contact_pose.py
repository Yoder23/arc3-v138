"""Contact experiments and fresh motion evidence, retaining earlier goal memories."""
from collections import Counter,defaultdict
import copy
from completed_pose_learner_v2 import Learner as Base,nonrect
from visual_transform_learner import public,unique,identity,canonical,digest

class Learner(Base):
    def __init__(self):
        super().__init__()
        self.contact_trials=Counter();self.keyboard_steps=0
        self.control_archives=[];self.boundary=None;self.boundary_row=0

    def observe(self,raw,action=None,data=None):
        obs=public(raw);old=copy.deepcopy(self.previous)
        progress=old is not None and obs['levels_completed']!=old['levels_completed']
        boundary=old is not None and action in (0,6)
        if boundary:
            self.control_archives.append(dict(models=copy.deepcopy(self.models),
                failed_goals=copy.deepcopy(self.failed),boundary=copy.deepcopy(self.boundary)))
            self.models=defaultdict(list);self.failed=set();self.pending=None
            self.keyboard_steps=0
            self.boundary=dict(before=old,after=copy.deepcopy(obs),action=action,data=copy.deepcopy(data or {}))
            self.boundary_row=len(self.rows)
            if action==6:
                y,x=data['y'],data['x']
                for key,p in self.perceive(old['frame']).items():
                    if nonrect(p) and (y-p[2][0],x-p[2][1]) in p[1]:
                        self.contact_trials[key]+=1
        elif action not in (None,0,6):self.keyboard_steps+=1
        super().observe(obs,action)
        if progress:
            self.contact_trials.clear();self.keyboard_steps=0
            self.control_archives=[];self.boundary=None;self.boundary_row=0

    def propose(self,raw):
        obs=public(raw)
        c=super().propose(obs)
        if c:
            c['motion_context_boundary']=copy.deepcopy(self.boundary)
            return c
        if obs['state']!='NOT_FINISHED' or 6 not in obs['available_actions'] or self.keyboard_steps<24:
            return None
        current=self.perceive(obs['frame']);choices=[]
        for key,p in current.items():
            if not nonrect(p):continue
            matches=any(q[0]!=p[0] and q[1]==p[1] for q in self.references)
            moving=any(s['delta']!=(0,0) for (k,a),rows in self.models.items() if k==key for s in rows)
            choices.append((self.contact_trials[key],not matches,not moving,key,p))
        if not choices:return None
        _,_,_,key,p=min(choices);dy,dx=p[1][len(p[1])//2]
        result=dict(kind='pose_contact_experiment',action=6,data=dict(y=p[2][0]+dy,x=p[2][1]+dx),
            actor=p,actor_key=key,context=digest(obs),
            scope='Foreground contact is an experiment. A new motion context requires new observed translation support.')

        if self.body_memory.templates:result['body_completion_sources']=self.body_memory.sources()
        return result

    def commit(self,c):
        if c['kind']=='retained_pose_alignment':super().commit(c)
