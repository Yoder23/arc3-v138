"""Retain geometric identities through marker occlusion using the observed selection badge."""
import copy
from collections import Counter
from cross_shape_geometry_v2 import scene,shape_points
from visual_transform_learner import digest
class Tracker:
    def __init__(self):self.level=None;self.objects={};self.targets={};self.badge=None;self.cache={};self.previous=None;self.selection_transitions={}
    def extract(self,obs):
        h=digest(obs)
        if h in self.cache:return copy.deepcopy(self.cache[h])
        raw,targets=scene(obs);f=obs['frame'];totals=Counter(v for row in f for v in row)
        if self.level!=obs['levels_completed'] or not self.objects:
            self.level=obs['levels_completed'];self.objects=copy.deepcopy(raw);self.targets=copy.deepcopy(targets);selected=[o for o in raw.values() if o['selected']]
            if len(selected)==1:self.badge=f[selected[0]['center'][0]][selected[0]['center'][1]]
        else:
            badge=[(y,x) for y,row in enumerate(f[:62]) for x,c in enumerate(row) if c==self.badge] if self.badge is not None else []
            old_active=[k for k,o in self.objects.items() if o['selected']];new={}
            for k,old in self.objects.items():
                centers=[tuple(old['center'])]
                moving=old_active==[k] and self.previous and self.previous['action'] in (1,2,3,4)
                if moving and self.previous.get('delta'):centers.insert(0,tuple(old['center'][i]+self.previous['delta'][i] for i in [0,1]))
                if k in raw:centers.insert(0,tuple(raw[k]['center']))
                if moving and len(badge)==1:centers.insert(0,badge[0])
                fits=[];bg=totals.most_common(1)[0][0]
                for center in dict.fromkeys(centers):
                    if not(0<=center[0]<62 and 0<=center[1]<64):continue
                    pts={p for p in shape_points(center,old['radius']) if 0<=p[0]<62 and 0<=p[1]<64}
                    counts=Counter(f[y][x] for y,x in pts);colors=[c for c in counts if c!=bg and c!=self.badge]
                    if not pts or not colors:continue
                    color=max(colors,key=lambda c:counts[c]);score=counts[color]/len(pts)
                    if score>=.6:fits.append((score,center,color))
                if fits:
                    score,center,color=max(fits,key=lambda q:q[0]);new[k]=dict(old,color=color,center=center,selected=(len(badge)==1 and center==badge[0]) or (not badge and old['selected'] and moving),retained_geometry=True)
            visible=[k for k,o in new.items() if o['selected']]
            if len(visible)>1 and self.previous and len(old_active)==1:
                chosen=old_active[0] if self.previous['action'] in (1,2,3,4) else self.selection_transitions.get(old_active[0])
                if chosen in visible:
                    for k in visible:new[k]['selected']=k==chosen
                    visible=[chosen]
            if self.previous and self.previous['action']==5 and len(old_active)==1:
                if len(visible)==1:self.selection_transitions[old_active[0]]=visible[0]
                elif not badge:
                    inferred=self.selection_transitions.get(old_active[0]);others=[k for k in new if k!=old_active[0]]
                    if inferred is None and len(others)==1:inferred=others[0]
                    if inferred in new:new[inferred]['selected']=True;new[inferred]['selection_is_hypothesis']=True
            self.objects=new
        value=(copy.deepcopy(self.objects),copy.deepcopy(self.targets));self.cache[h]=value;return copy.deepcopy(value)
    def commit(self,action,delta=None):self.previous=dict(action=action,delta=delta)
