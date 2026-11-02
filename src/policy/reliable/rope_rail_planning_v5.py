"""Compose observed rope motion rules against visible labeled rail goals."""
import heapq,itertools
from rope_motion_hypotheses_v2 import scene,step
from rope_visible_parts_v1 import parts

def goals(o,c):
 ps=parts(o['frame']);leg=sorted([p for p in ps if p['y']>=54 and p['h']==p['w']==6 and p['area']==30],key=lambda p:p['x']);out=[]
 for j,l in enumerate(leg):
  marks=[p for p in ps if p['h']==p['w']==2 and p['area']==4 and l['x']<=p['x']<l['x']+6 and l['y']<=p['y']<l['y']+6]
  if len(marks)!=1:return []
  markers=[p for p in ps if p['h']==p['w']==2 and p['area']==4 and p['color']==marks[0]['color'] and p['y']<5]
  if len(markers)!=1:return []
  rail=next((r for r in c['rails'] if r[0]+1==markers[0]['x']),None)
  if not rail:return []
  end=leg[j+1]['x'] if j+1<len(leg) else 64
  seq=sorted([p for p in ps if p['h']==p['w']==4 and p['area'] in (12,16) and p['y']>=54 and l['x']<p['x']<end],key=lambda p:p['x'])
  out.append(dict(rail=rail,colors=[p['color'] for p in seq],legend=l,marker=markers[0]))
 return out

def targets(c,gs):
 groups=[]
 for g in gs:
  x,top,bottom=g['rail'];rows=[y for y in range(c['bounds'][0]+1,c['bounds'][1]+2,6) if top<=y<=bottom]
  groups.append([dict(zip(g['colors'],[(y,x) for y in ys])) for ys in itertools.combinations(rows,len(g['colors']))])
 result=[]
 for choice in itertools.product(*groups):
  merged={k:v for q in choice for k,v in q.items()}
  if set(merged)==set(c['colors']):result.append(tuple(v for k in c['colors'] for v in merged[k]))
 return result

def plan(s,c,gs,limit=120000):
 ts=targets(c,gs)
 if not ts:return [],dict(expanded=0,reason='no_visible_goal_assignment')
 targetset=set(ts)
 def h(st):
  return min(sum(abs(a-b) for a,b in zip(st[2:],t))/6 for t in ts)
 counter=itertools.count();q=[(4*h(s),next(counter),s)];cost={s:0};parent={};expanded=0
 while q and expanded<limit:
  _,_,u=heapq.heappop(q);expanded+=1
  if u[2:] in targetset:
   actions=[]
   while u!=s:u,a0=parent[u];actions.append(a0)
   return actions[::-1],dict(expanded=expanded,reason='visible_rail_assignment')
  for a in (1,2,3,4):
   v=step(u,a,c);nd=cost[u]+1
   if v==u or nd>=cost.get(v,10**9):continue
   cost[v]=nd;parent[v]=(u,a);heapq.heappush(q,(nd+4*h(v),next(counter),v))
 return [],dict(expanded=expanded,reason='search_limit',frontier=len(q))
