"""Retained line motion plus observed constant-perimeter rectangle geometry."""
import copy,itertools
from component_figure_model_v4 import pixels,fit_figure,goal_specs,estimate,ignore_mask,advance as line_advance,plan as line_plan
from rectangle_contact_model_v2 import points,advance as rect_advance,goal_boxes,plan as rect_plan
from rectangle_observation_v1 import bounds

def assignment(figures,rect,sc):
 choices=[]
 for order in itertools.permutations(sorted(map(int,sc['targets']))):
  score=0;valid=True
  for i,(f,c) in enumerate(zip(figures,order)):
   targets=sc['targets'][c]
   if i==rect:
    goals=goal_boxes(f['state'],targets)
    if not goals:valid=False;break
    score+=min(sum(abs(a-b) for a,b in zip(f['state'],q)) for q in goals)/6
   else:
    specs=goal_specs(f['state'],f['segments'],targets)
    if not specs:valid=False;break
    score+=estimate(f['state'],specs)
  if valid:choices.append((score,order))
 return list(min(choices)[1]) if choices else None

def covered(f,target,sc,rect=False):
 cells=points(f['state']) if rect else set.union(*pixels(f['state'],f['segments']))
 return f['color']==target and set(map(tuple,sc['targets'][target]))<=cells

def paint(cells,color,pads):
 touched={p['color'] for p in pads if any(p['y']-1<=y<p['y']+p['size']+1 and p['x']-1<=x<p['x']+p['size']+1 for y,x in cells)}
 return next(iter(touched)) if len(touched)==1 else color

def advance(f,delta,sc,rect,mechanism):
 site=set(map(tuple,sc['site']['points']))
 if rect:
  s=rect_advance(f['state'],delta,site,mechanism);return dict(f,state=list(s),color=paint(points(s),f['color'],sc['paints']))
 q=line_advance(f['state'],f['color'],delta,f['segments'],site,sc['paints'])
 return dict(f,state=list(q[0]),color=q[1]) if q else None

def selected(figures,rect,frame):
 badge=[(y,x) for y,row in enumerate(frame[:62]) for x,c in enumerate(row) if c==0]
 if len(badge)!=1:return None
 hits=[]
 for i,f in enumerate(figures):
  if i==rect:
   a,b,c,d=f['state'];anchor=(a+((c-a)//3+1)//2*3,b+((d-b)//3+1)//2*3)
  else:anchor=tuple(f['state'][:2])
  if anchor==badge[0]:hits.append(i)
 return hits[0] if len(hits)==1 else None

def fit_rect(box,color,frame,sc,othercolors=()):
 mask=ignore_mask(sc);expected={p for p in points(box) if 0<=p[0]<62 and 0<=p[1]<64}-mask;actual={(y,x) for y,row in enumerate(frame[:62]) for x,c in enumerate(row) if c==color}-mask
 return bool(expected) and not actual-expected and len(expected&actual)>=.6*len(expected) and all(frame[y][x] in set(othercolors)|{0} for y,x in expected-actual)

def observe(figures,rect,sc,frame,action,models,active,mechanism):
 new=copy.deepcopy(figures)
 if action==5:
  for i,f in enumerate(figures):
   other=[q['color'] for j,q in enumerate(figures) if j!=i]
   if not (fit_rect(f['state'],f['color'],frame,sc,other) if i==rect else fit_figure(f,frame,sc,other)):return None
  return new,selected(new,rect,frame),dict(kind='selection')
 if active is None:return None
 f=figures[active];expected=advance(f,models[action]['delta'],sc,active==rect,mechanism)
 colors={v for row in frame[:62] for v in row}-{sc['background'],0,sc['site']['color'],2,4};other=[q['color'] for i,q in enumerate(figures) if i!=active];hits=[]
 if active==rect:
  seen=set()
  for color in sorted(colors-set(other)):
   candidates=[expected['state']] if expected else []
   box=bounds(frame,color,sc)
   if box is not None:candidates.append(box)
   for box in candidates:
    k=(tuple(box),color)
    if k in seen:continue
    seen.add(k)
    if box[2]-box[0]+box[3]-box[1]==f['perimeter'] and fit_rect(box,color,frame,sc,other):hits.append(dict(f,state=box,color=color))
 else:
  candidates=[]
  if expected:candidates.append(expected)
  delta=models[action]['delta']
  for mask in itertools.product((0,1),repeat=len(f['segments'])):
   s=[v+delta[k%2]*mask[k//2] for k,v in enumerate(f['state'])]
   for color in sorted(colors-set(other)):candidates.append(dict(f,state=s,color=color))
  seen=set()
  for q in candidates:
   k=(tuple(q['state']),q['color'])
   if k in seen:continue
   seen.add(k)
   if fit_figure(q,frame,sc,other):hits.append(q)
 if len(hits)!=1:return None
 new[active]=hits[0];confirmed=expected is not None and expected['state']==hits[0]['state'] and expected['color']==hits[0]['color']
 return new,active,dict(kind='confirmed' if confirmed else 'alternative',figure=active,before=f,after=hits[0])

def plan(f,target,rect,sc,models,mechanism,blocked=()):
 if rect:return rect_plan(f['state'],f['color'],target,sc['targets'][target],set(map(tuple,sc['site']['points'])),sc['paints'],models,mechanism,blocked=blocked)
 return line_plan(f,target,sc,models,limit=150000,blocked=blocked)
