"""Shared separator and cell ontology for static and interactive scenes."""
from functools import lru_cache
import numpy as np

def freeze(a):return tuple(tuple(map(int,row)) for row in a)

def runs(mask):
    values=[];start=None
    for i,take in enumerate(list(mask)+[False]):
        if take and start is None:start=i
        if not take and start is not None:values.append((start,i));start=None
    return values


@lru_cache(maxsize=512)
def partition(g,separator):
    a=np.asarray(g,dtype=np.int16)
    if separator=='auto':
        options=[]
        for c in np.unique(a):
            rows=np.all(a==c,axis=1);cols=np.all(a==c,axis=0)
            rs=runs(~rows);cs=runs(~cols)
            if rows.any() and cols.any() and len(rs)*len(cs)>=2:options.append((len(rs)*len(cs),int(rows.sum()+cols.sum()),-int(c)))
        if not options:raise ValueError('No repeated cell partition')
        separator=-max(options)[2]
    rows=np.all(a==separator,axis=1);cols=np.all(a==separator,axis=0)
    rs=runs(~rows);cs=runs(~cols)
    if not rs or not cs or len(rs)*len(cs)<2 or max(len(rs),len(cs))>12 or not (rows.any() or cols.any()):raise ValueError('Invalid cell partition')
    return int(separator),rs,cs

