"""Immutable, action-conditioned visible-effect memory for variable click targets."""
import math
import numpy as np
from collections import Counter


def key(frame,x,y):
    a=np.asarray(frame);h,w=a.shape;y=min(h-1,y);x=min(w-1,x)
    color=int(a[y,x]);neighbors=[]
    # Relative color equality is palette invariant; retain the clicked color as
    # a per-episode binding, never a benchmark-specific semantic assignment.
    for dy,dx in ((-3,0),(3,0),(0,-3),(0,3),(-7,0),(7,0),(0,-7),(0,7)):
        yy,xx=y+dy,x+dx
        neighbors.append(int(0<=yy<h and 0<=xx<w and a[yy,xx]==color))
    return (color,*neighbors)


class GroundedEffects:
    def __init__(self):self.episodes=();self.statistics={};self.used=0
    def observe(self,before,action,after,state):
        if action[0]!=6:return
        k=key(before,action[1],action[2]);changed=bool(np.any(np.asarray(before)!=np.asarray(after)))
        # Multiple occurrences in an identical state are one evidence unit.
        stats=self.statistics.setdefault(k,{})
        if state not in stats:stats[state]=[0,0]
        stats[state][int(changed)]+=1
        self.episodes=self.episodes+((k,state,changed),)
    def value(self,frame,action):
        if action[0]!=6:return 0.
        stats=self.statistics.get(key(frame,action[1],action[2]),{})
        positives=sum(bool(v[1]) for v in stats.values())
        negatives=sum(bool(v[0]) and not v[1] for v in stats.values())
        count=positives+negatives
        if count<2:return 0.
        self.used+=1
        probability=(positives+1)/(count+2)
        # Confidence influences order, never prohibits an unexplored action.
        confidence=min(1.,count/8.)
        return 2.*confidence*(probability-.5)
