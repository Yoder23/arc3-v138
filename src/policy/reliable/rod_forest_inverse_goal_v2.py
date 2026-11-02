"""Backward goal geometry constrains forward, observed-action planning."""
import heapq
from rod_forest_model_v6 import joint,constraints,predict,valid

def targets(sc,tree,models):
 unfinished=[(i,e) for i,e in zip(tree['endpoints'],sc['ends']) if e['point'] not in sc['goals']];remaining=[g for g in sc['goals'] if not any(e['point']==g for e in sc['ends'])]
 if len(unfinished)!=1 or len(remaining)!=1:return [],[]
 leaf=unfinished[0][0];goal=remaining[0];parents={b:a for a,b in tree['edges']};chain=[leaf]
 while chain[-1] in parents:chain.append(parents[chain[-1]])
 chain=chain[::-1];start=sc['state'];limits=constraints(sc);pref=limits['walls'];n=len(sc['bodies']);dirs=[(0,1),(1,0),(0,-1),(-1,0)];turnable={m['model']['index'] for m in models.values() if m['model']['mode'] in ('rotate','rotate_joint')};movable={m['model']['index'] for m in models.values() if m['model']['mode']=='extend'}
 def direction(i):v=start[6*i:6*i+6];return (-v[5],-v[4])
 offsets={i:(dirs.index(direction(i))-dirs.index(direction(parents[i])))%4 for i in chain if i in parents}
 def box(v):
  y,x,h,w,dx,dy=v;return (y-(dy<0),x-(dx<0),y+h+(dy>0),x+w+(dx>0))
 static=[box(start[6*i:6*i+6]) for i in range(n) if i not in chain];out=[]
 def clear(v,boxes):
  a,b,c,d=box(v)
  if a<0 or b<0 or c>limits['height'] or d>64:return False
  if pref[c][d]-pref[a][d]-pref[c][b]+pref[a][b]:return False
  return not any(max(a,z[0])<min(c,z[2]) and max(b,z[1])<min(d,z[3]) for z in boxes)
 def recurse(k,point,parent_dir,state,boxes):
  i=chain[k];cy,cx=point;old=start[6*i:6*i+6];oldlen=old[3] if old[4] else old[2];options=range(4) if i in turnable else ([dirs.index(direction(i))] if k==0 else [(parent_dir+offsets[i])%4])
  for d in options:
   dy,dx=dirs[d]
   if i==leaf:
    yy,xx=goal[0]-cy,goal[1]-cx
    if yy*dx-xx*dy:continue
    length=yy*dy+xx*dx+2;lengths=[length] if length>=2 and (length-oldlen)%3==0 and (i in movable or length==oldlen) else []
   else:lengths=range(2+(oldlen-2)%3,64,3) if i in movable else [oldlen]
   for length in lengths:
    v=[cy-1,cx if dx>0 else cx-length+1,3,length,-dx,0] if dx else [cy if dy>0 else cy-length+1,cx-1,length,3,0,-dy]
    if not clear(v,boxes):continue
    ns=list(state);ns[6*i:6*i+6]=v
    if i==leaf:
     j=tree['endpoints'].index(leaf);ns[6*n+2*j:6*n+2*j+2]=goal;out.append(tuple(ns))
    else:recurse(k+1,(cy+dy*(length+1),cx+dx*(length+1)),d,ns,boxes+[box(v)])
 recurse(0,joint(start[6*chain[0]:6*chain[0]+6]),None,list(start),static)
 return out,chain

def plan(sc,tree,models,blocked=(),limit=150000):
 ts,chain=targets(sc,tree,models)
 if not ts:return [],dict(reason='no_valid_goal_configuration',targets=0)
 start=tuple(sc['state']);limits=constraints(sc);selected={k:m for k,m in models.items() if m['model']['index'] in chain}
 def distance(a,b):
  total=0
  for i in chain:
   va=a[6*i:6*i+6];vb=b[6*i:6*i+6];ja=joint(va);jb=joint(vb);total+=(abs(ja[0]-jb[0])+abs(ja[1]-jb[1]))/(3*len(chain));total+=abs((va[3] if va[4] else va[2])-(vb[3] if vb[4] else vb[2]))/3;total+=sum(x!=y for x,y in zip(va[4:],vb[4:]))
  return total
 ts=sorted(ts,key=lambda t:distance(start,t))[:64];targetset=set(ts)
 def h(s):return min(distance(s,t) for t in ts)
 q=[(2*h(start),0,start)];cost={start:0};previous={};expanded=0
 while q and expanded<limit:
  _,g,s=heapq.heappop(q)
  if g!=cost[s]:continue
  expanded+=1
  if s in targetset:
   path=[]
   while s!=start:s,k=previous[s];path.append(k)
   return path[::-1],dict(reason='inverse_goal_configuration',targets=len(ts),expanded=expanded)
  for key,m in selected.items():
   if len(m['support'])<2 or (s,key) in blocked:continue
   z=m['model'];t=predict(s,z['index'],z['mode'],z['amount'],tree,limits,z['descendants'])
   if t is None or cost.get(t,10**9)<=g+1:continue
   cost[t]=g+1;previous[t]=(s,key);heapq.heappush(q,(g+1+2*h(t),g+1,t))
 return [],dict(reason='inverse_search_limit',targets=len(ts),expanded=expanded,frontier=len(q))
