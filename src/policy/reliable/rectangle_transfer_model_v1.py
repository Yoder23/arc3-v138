import copy,itertools
from rectangle_contact_model_v2 import points,goal_boxes,advance as rect_advance
from rectangle_contact_model_v3 import plan as rect_plan
from elastic_figure_model_v1 import fit_rect,paint
from rectangle_observation_v1 import bounds

def selected(figs,frame):
 badges=[(y,x) for y,row in enumerate(frame[:62]) for x,c in enumerate(row) if c==0];hits=[]
 for i,f in enumerate(figs):
  a,b,c,d=f['state'];anchor=(a+((c-a)//3+1)//2*3,b+((d-b)//3+1)//2*3)
  if anchor in badges:hits.append(i)
 return hits[0] if len(hits)==1 else None

def advance(f,action,sc,models,mechanism):
 q=rect_advance(f['state'],models[action]['delta'],set(map(tuple,sc['site']['points'])),mechanism)
 return dict(f,state=list(q),color=paint(points(q),f['color'],sc['paints']))

def covered(f,target,sc):return f['color']==target and set(map(tuple,sc['targets'][target]))<=points(f['state'])

def assignment(figs,sc):
 choices=[]
 for order in itertools.permutations(sorted(sc['targets'])):
  goals=[goal_boxes(f['state'],sc['targets'][c]) for f,c in zip(figs,order)]
  if all(goals):choices.append((sum(min(sum(abs(a-b) for a,b in zip(f['state'],g)) for g in gs) for f,gs in zip(figs,goals)),order))
 return list(min(choices)[1]) if choices else None

def observe(figs,active,frame,action,sc,models,mechanism):
 other=lambda i:[f['color'] for j,f in enumerate(figs) if j!=i]
 if action==5:
  if all(fit_rect(f['state'],f['color'],frame,sc,other(i)) for i,f in enumerate(figs)):return copy.deepcopy(figs),selected(figs,frame),dict(kind='selection')
  return None
 if active is None:return None
 f=figs[active];pred=advance(f,action,sc,models,mechanism);colors={v for row in frame[:62] for v in row}-{sc['background'],0,1,2,4}-set(other(active));hits=[];seen=set()
 for color in sorted(colors):
  raw=bounds(frame,color,sc)
  for q in [pred['state']]+([raw] if raw else []):
   k=(tuple(q),color)
   if k in seen:continue
   seen.add(k)
   if q[2]-q[0]+q[3]-q[1]==f['perimeter'] and fit_rect(q,color,frame,sc,other(active)):hits.append(dict(f,state=q,color=color))
 if len(hits)!=1:return None
 new=copy.deepcopy(figs);new[active]=hits[0];outcome=dict(kind='confirmed' if pred==hits[0] else 'alternative',figure=active,before=f,after=hits[0]);return new,active,outcome

def plan(figs,i,target,sc,models,mechanism,blocked):
 f=figs[i];return rect_plan(f['state'],f['color'],target,sc['targets'][target],set(map(tuple,sc['site']['points'])),sc['paints'],models,mechanism,blocked=blocked,forbidden_colors={q['color'] for j,q in enumerate(figs) if j!=i},limit=120000)
