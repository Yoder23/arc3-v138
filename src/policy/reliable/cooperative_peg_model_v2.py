"""Compose ordinary jumps with a movable, non-consuming helper token."""
from collections import deque

def search(cells,ordinary,helpers,pitch,limit=120000,goal_carriers=None):
 cells=set(map(tuple,cells));initial=(frozenset(map(tuple,ordinary)),frozenset(map(tuple,helpers)));todo=deque([initial]);parent={initial:None};edge={};expanded=0
 while todo and expanded<limit:
  marks,assist=todo.popleft();state=(marks,assist);expanded+=1
  if (len(marks)<=1 if goal_carriers is None else bool(marks|assist) and (marks|assist)<=set(map(tuple,goal_carriers))):
   path=[]
   while parent[state]is not None:path.append(edge[state]);state=parent[state]
   return list(reversed(path)),dict(expanded=expanded,seen=len(parent),exhausted=False)
  occupied=marks|assist
  for a in sorted(occupied):
   for dy,dx in[(-pitch,0),(pitch,0),(0,-pitch),(0,pitch)]:
    b=(a[0]+dy,a[1]+dx);z=(a[0]+2*dy,a[1]+2*dx)
    if b not in occupied or z in occupied or z not in cells:continue
    actor='helper'if a in assist else'ordinary';preserve=a in assist or b in assist
    m=(marks-{a}-{b})|{z}if not preserve else(marks-{a})|{z}if a in marks else marks
    h=(assist-{a})|{z}if a in assist else assist
    key=(frozenset(m),frozenset(h))
    if key in parent:continue
    parent[key]=state;edge[key]=dict(jump=(a,b,z),actor=actor,preserves_intermediate=preserve,ordinary_after=sorted(m),helpers_after=sorted(h));todo.append(key)
 return None,dict(expanded=expanded,seen=len(parent),exhausted=not todo)
