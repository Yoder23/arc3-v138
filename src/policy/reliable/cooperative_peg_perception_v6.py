from collections import Counter
from paired_carrier_geometry_v2 import scene,positions
from binary_demonstration_bootstrap_v1 import components

def retained_scene(frame,rule):
 s=scene(frame)
 if s and not(s['size']==rule['size']and s['field']==rule['field']and s['pitch']>rule['pitch']and s['pitch']%rule['pitch']==0):return dict(s,mark=rule['ordinary_ink'])
 # Sparse visible cells can alias the demonstrated lattice to a larger multiple.
 # Preserve the learned spacing when size/field agree and reconstruct its cells.
 n=rule['size'];field=rule['field'];pitch=rule['pitch'];seeds=[o['box'][:2]for o in components(frame)if not o.get('parts')and o['ink']==field and o['box'][2]==o['box'][3]==n and len(o['shape'])==n*n]
 if not seeds:
  seeds=list(positions(frame,n,rule.get('carrier_ink',-1)))
 if not seeds:return None
 oy,ox=seeds[0][0]%pitch,seeds[0][1]%pitch
 cells=[(y,x)for y in range(oy,65-n,pitch)for x in range(ox,65-n,pitch)if all(frame[y+dy][x+dx]==field for dy,dx in[(0,0),(0,n-1),(n-1,0),(n-1,n-1)])]
 return dict(cells=cells,pitch=pitch,size=n,field=field,mark=rule['ordinary_ink'])
def view(raw,rule,carrier_ink):
 s=retained_scene(raw['frame'],rule)
 if not s:return None
 n=s['size'];k=(n-1)//2;f=raw['frame'];bodies=positions(f,n,carrier_ink);cells=sorted(set(map(tuple,s['cells']))|set(bodies))
 marks=[p for p in cells if f[p[0]+k][p[1]+k]==rule['ordinary_ink']];helpers=[p for p in cells if f[p[0]+k][p[1]+k]==rule['helper_ink']]
 return dict(scene=s,cells=cells,ordinary=marks,helpers=helpers,carrier_positions=bodies)
def rail_trials(raw,v,controls,preferred=None,excluded=()):
 f=raw['frame'];n=v['scene']['size'];k=(n-1)//2;pos=tuple(sorted(v['carrier_positions']));occupied=set(pos);static=set(v['scene']['cells']);background=Counter(x for row in f[1:]for x in row).most_common(1)[0][0];out=[]
 for delta,action in sorted(controls.items()):
  if action in excluded:continue
  predicted={};support=[]
  for p in pos:
   q=tuple(p[j]+delta[j]for j in(0,1));y,x=q;allowed=q in occupied
   if not allowed and q not in static and 0<=y<=64-n and 0<=x<=64-n:
    colors={f[yy][xx]for yy in(y+k,y+k+1)for xx in(x+k,x+k+1)}
    allowed=len(colors)==1 and next(iter(colors))not in(background,v['scene']['field'],v['scene']['mark'])
    if allowed:support.append(dict(position=q,ink=next(iter(colors))))
   predicted[p]=q if allowed else p
  while True:
   counts=Counter(predicted.values());bad={q for q,n in counts.items()if n>1}
   updates={p:p for p,q in predicted.items()if q in bad and q!=p}
   if not updates:break
   predicted.update(updates)
  moving=[p for p in pos if predicted[p]!=p]
  if moving and len(set(predicted.values()))==len(pos):out.append(dict(delta=delta,action=action,positions_before=pos,positions_predicted=sorted(predicted.values()),moving=moving,stationary=[p for p in pos if p not in moving],rail_support=support,hypothesis='test_independently_supported_carrier_motion'))
 return sorted(out,key=lambda v:(tuple(v['delta'])!=tuple(preferred or()),v['delta']))
def rail_trial(raw,v,controls,preferred=None,excluded=()):
 out=rail_trials(raw,v,controls,preferred,excluded);return out[0]if out else None

def enrich(raw,v,permanent_rules,track):
 f=raw['frame'];n=v['scene']['size'];pitch=v['scene']['pitch'];k=(n-1)//2;anchors=v['carrier_positions']or v['scene']['cells']
 if not anchors:return dict(v,pivots=[],rails=[],permanent_rules=permanent_rules,track=track)
 oy,ox=anchors[0][0]%pitch,anchors[0][1]%pitch;pivots=[];rails=set(map(tuple,v['carrier_positions']))
 for y in range(oy,65-n,pitch):
  for x in range(ox,65-n,pitch):
   if all(f[yy][xx]==track for yy in(y+k,y+k+1)for xx in(x+k,x+k+1)):rails.add((y,x))
   for rule in permanent_rules:
    if rule['size']!=n or y<1:continue
    pattern=[row[1:n+1]for row in rule['patch'][:n]]
    if [row[x:x+n]for row in f[y-1:y+n-1]]==[list(row)for row in pattern]:pivots.append((y,x));break
 return dict(v,pivots=sorted(set(pivots)),rails=sorted(rails),permanent_rules=permanent_rules,track=track)
