"""Treat changed interior markers as new experimental control contexts."""
from collections import Counter,defaultdict
import copy
import numpy as np
from scipy.ndimage import binary_fill_holes
from completed_contact_pose_v3 import Learner as Base
from retained_pose_learner_v2 import nonrect
from visual_transform_learner import public,unique

def marker_changes(before,after):
    if before['state']!=after['state'] or before['state']!='NOT_FINISHED':return []
    if before['levels_completed']!=after['levels_completed']:return []
    left,right=unique(before['frame']),unique(after['frame']);out=[]
    for key in sorted(left.keys()&right.keys()):
        a,b=left[key],right[key]
        if a!=b or not nonrect(a):continue
        h=max(y for y,x in a[1])+1;w=max(x for y,x in a[1])+1
        mask=np.zeros((h,w),bool)
        for y,x in a[1]:mask[y,x]=True
        holes=np.argwhere(binary_fill_holes(mask)&~mask).tolist()
        if not holes:continue
        old=tuple(before['frame'][a[2][0]+y][a[2][1]+x] for y,x in holes)
        new=tuple(after['frame'][a[2][0]+y][a[2][1]+x] for y,x in holes)
        if old!=new:out.append(dict(body=a,holes=holes,before=old,after=new))
    return out

class Learner(Base):
    def __init__(self):
        super().__init__();self.context_probes=None;self.marker_boundaries=[]

    def observe(self,raw,action=None,data=None):
        obs=public(raw);old=self.previous
        changes=marker_changes(old,obs) if old and action in (1,2,3,4,5,7) else []
        if changes:
            self.control_archives.append(dict(models=copy.deepcopy(self.models),
                failed_goals=copy.deepcopy(self.failed),boundary=copy.deepcopy(self.boundary)))
            self.models=defaultdict(list);self.pending=None;self.failed=set()
        super().observe(obs,action,data)
        if changes:
            self.boundary=dict(before=copy.deepcopy(old),after=copy.deepcopy(obs),action=action,data=copy.deepcopy(data or {}))
            self.boundary_row=len(self.rows);self.keyboard_steps=0
            self.marker_boundaries.append(dict(boundary=copy.deepcopy(self.boundary),changes=changes))
            # A changed display is a context hypothesis, not proof of a switch.
            # Try other available controls before undoing that intervention.
            self.context_probes=Counter({action:8})
        if action==0:self.context_probes=None
        if old and old['levels_completed']!=obs['levels_completed']:
            self.context_probes=None;self.marker_boundaries=[]

    def choose(self,raw):
        obs=public(raw)
        if self.context_probes is None or obs['state']!='NOT_FINISHED':return super().choose(obs)
        cert=self.propose(obs)
        if cert:self.commit(cert);return cert['action']
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
        if not legal:return super().choose(obs)
        action=min(legal,key=lambda a:(self.context_probes[a]//2,a));self.context_probes[action]+=1
        return action
