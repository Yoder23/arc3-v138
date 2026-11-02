"""Hypotheses for separately blocked line segments and whole-figure color conversion."""
import heapq,itertools

def pixels(state,segments):
 return [{(state[2*i]+(d if p['axis'] else 0),state[2*i+1]+(0 if p['axis'] else d)) for d in range(-p['half'],p['half']+1)} for i,p in enumerate(segments)]

def goal_specs(state,segments,targets,step=3):
 out=[]
 for assignment in itertools.product(range(len(segments)),repeat=len(targets)):
  bounds=[];good=True
  for i,p in enumerate(segments):
   assigned=[t for t,j in zip(targets,assignment) if j==i];y,x=state[2*i:2*i+2];r=p['half'];by=[r if p['axis'] else 0,61-r if p['axis'] else 61];bx=[0 if p['axis'] else r,63 if p['axis'] else 63-r]
   if assigned:
    if p['axis']==0:
     ys={t[0] for t in assigned}
     if len(ys)!=1:good=False;break
     by=[next(iter(ys))]*2;bx=[max(bx[0],max(t[1] for t in assigned)-r),min(bx[1],min(t[1] for t in assigned)+r)]
    else:
     xs={t[1] for t in assigned}
     if len(xs)!=1:good=False;break
     bx=[next(iter(xs))]*2;by=[max(by[0],max(t[0] for t in assigned)-r),min(by[1],min(t[0] for t in assigned)+r)]
   by=[by[0]+(y-by[0])%step,by[1]-(by[1]-y)%step];bx=[bx[0]+(x-bx[0])%step,bx[1]-(bx[1]-x)%step]
   if by[0]>by[1] or bx[0]>bx[1]:good=False;break
   bounds.append(tuple(by+bx))
  if good:out.append(tuple(bounds))
 return sorted(set(out))

def assignment(sc,models):
 colors=sorted(sc['targets']);figs=sc['figures'];result=[]
 for order in itertools.permutations(colors):
  good=True;score=0
  for p,c in zip(figs,order):
   specs=goal_specs(p['state'],p['segments'],sc['targets'][c])
   if not specs:good=False;break
   score+=estimate(p['state'],specs)+100*min(sum((b[0]==b[1]) if seg['axis']==0 else (b[2]==b[3]) for b,seg in zip(spec,p['segments'])) for spec in specs)
  if good:result.append((score,order))
 return min(result)[1] if result else None

def estimate(s,specs):
 return min(max(max(a-s[2*i],0,s[2*i]-b)+max(c-s[2*i+1],0,s[2*i+1]-d) for i,(a,b,c,d) in enumerate(spec)) for spec in specs)/3

def advance(s,color,delta,segments,site,pads,margin=1):
 out=list(s)
 for i,pts in enumerate(pixels(s,segments)):
  if not {(y+delta[0],x+delta[1]) for y,x in pts}&site:out[2*i]+=delta[0];out[2*i+1]+=delta[1]
 pts=set.union(*pixels(out,segments))
 if not all(0<=out[2*i]<62 and 0<=out[2*i+1]<64 for i in range(len(segments))):return None
 touched=[p['color'] for p in pads if any(p['y']-margin<=y<p['y']+p['size']+margin and p['x']-margin<=x<p['x']+p['size']+margin for y,x in pts)]
 if len(set(touched))>1:return None
 return tuple(out),touched[0] if touched else color

def plan(fig,target,sc,models,limit=120000,blocked=()):
 start=tuple(fig['state']);color=fig['color'];segments=fig['segments'];specs=goal_specs(start,segments,sc['targets'][target]);site=set(map(tuple,sc['site']['points']));goals=set(map(tuple,sc['targets'][target]));pads=sc['paints'];validcolors={color,target}
 if not specs:return None,dict(reason='no_geometric_assignment')
 def h(s,c):
  d=estimate(s,specs)
  if c!=target:
   p=next(p for p in pads if p['color']==target);pts=set.union(*pixels(s,segments));dist=min(max(p['y']-1-y,0,y-p['y']-p['size'])+max(p['x']-1-x,0,x-p['x']-p['size']) for y,x in pts)/3;d=max(d,dist)
  return d
 queue=[(2*h(start,color),0,start,color,[])];cost={(start,color):0};expanded=0
 while queue and expanded<limit:
  _,g,s,c,path=heapq.heappop(queue)
  if cost[s,c]!=g:continue
  expanded+=1
  if c==target and goals<=set.union(*pixels(s,segments)):return path,dict(expanded=expanded)
  for a,m in sorted(models.items()):
   if (tuple(s),c,a) in blocked:continue
   q=advance(s,c,m['delta'],segments,site,pads)
   if q is None:continue
   nxt,nc=q
   if nc not in validcolors or cost.get(q,10**9)<=g+1:continue
   cost[q]=g+1;heapq.heappush(queue,(g+1+2*h(nxt,nc),g+1,nxt,nc,path+[a]))
 return None,dict(expanded=expanded,frontier=len(queue))


def ignore_mask(sc):
 mask={(y,x) for p in sc['paints'] for y in range(p['y']-1,p['y']+p['size']+1) for x in range(p['x']-1,p['x']+p['size']+1)}
 mask|={(y+dy,x+dx) for ps in sc['targets'].values() for y,x in ps for dy in (-1,0,1) for dx in (-1,0,1)}
 return mask|set(map(tuple,sc['site']['points']))

def fit_figure(fig,frame,sc,othercolors):
 expected={p for pts in pixels(fig['state'],fig['segments']) for p in pts if 0<=p[0]<62 and 0<=p[1]<64}-ignore_mask(sc)
 observed={(y,x) for y,row in enumerate(frame[:62]) for x,c in enumerate(row) if c==fig['color']}-ignore_mask(sc)
 if not expected or observed-expected:return False
 return len(expected&observed)>=.55*len(expected) and all(frame[y][x] in set(othercolors)|{0} for y,x in expected-observed)

def selected(figures,frame):
 badge=[(y,x) for y,row in enumerate(frame[:62]) for x,c in enumerate(row) if c==0]
 if len(badge)!=1:return None
 q=badge[0];hits=[]
 for i,p in enumerate(figures):
  s=p['state'];anchor=tuple(s[:2]) if p['kind']=='plus' else ((s[0]+s[2])//2,(s[5]+s[7])//2)
  if q==anchor:hits.append(i)
 return hits[0] if len(hits)==1 else None

def observe(figures,sc,frame,action,models,active):
 import copy
 if action==5:
  if not all(fit_figure(p,frame,sc,[q['color'] for j,q in enumerate(figures) if j!=i]) for i,p in enumerate(figures)):return None
  return copy.deepcopy(figures),selected(figures,frame),dict(kind='selection')
 delta=models[action]['delta'];candidates=[];colors={v for row in frame[:62] for v in row}-{sc['background'],0,sc['site']['color'],2,4};site=set(map(tuple,sc['site']['points']))
 for i,p in enumerate(figures):
  if any(not fit_figure(q,frame,sc,[z['color'] for k,z in enumerate(figures) if k!=j]+list(colors)) for j,q in enumerate(figures) if j!=i):continue
  predicted=advance(p['state'],p['color'],delta,p['segments'],site,sc['paints']);states=[]
  if predicted:states.append((predicted[0],predicted[1],'predicted'))
  for mask in itertools.product((0,1),repeat=len(p['segments'])):
   ss=tuple(v+delta[k%2]*mask[k//2] for k,v in enumerate(p['state']))
   for c in sorted(colors):states.append((ss,c,'alternative'))
  seen=set()
  for ss,c,kind in states:
   if (ss,c) in seen:continue
   seen.add((ss,c));new=dict(p,state=list(ss),color=c)
   if fit_figure(new,frame,sc,[q['color'] for j,q in enumerate(figures) if j!=i]):
    changed=tuple(ss)!=tuple(p['state']) or c!=p['color'];candidates.append((changed,kind=='predicted',i,new,kind))
 if not candidates:return None
 moving=[q for q in candidates if q[0]]
 if moving:candidates=moving
 elif active is not None:candidates=[q for q in candidates if q[2]==active]
 if not candidates:return None
 preferred=[q for q in candidates if q[1]]
 if preferred:candidates=preferred
 if len(candidates)!=1:return None
 _,_,i,new,kind=candidates[0];out=copy.deepcopy(figures);out[i]=new
 return out,i,dict(kind=kind,figure=i,before=figures[i],after=new)
