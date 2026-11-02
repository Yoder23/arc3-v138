"""Synthesize tentative nested sequences from visible goal symbols and editable groups."""
from centered_symbol_rows_v1 import tokens,layouts
from collections import Counter,defaultdict
from indirect_word_geometry_v1 import frames,enclosed,border

def center(t):
 y,x,h,w=t['core'];return (x+(w-1)//2,y+(h-1)//2)
def ring_color(f,t):
 y,x,h,w=t['core'];colors={f[v][u]for v,u in border((y-1,x-1,h+2,w+2))}
 return next(iter(colors))if len(colors)==1 and f[y][x]not in colors else None

def scene(o):
 f=o['frame'];ts=tokens(f);groups=[]
 for box,color in frames(f):
  if min(box[:2])<=0 or box[0]+box[2]>=len(f)or box[1]+box[3]>=len(f[0]):continue
  inner=sorted([t for t in ts if enclosed(t['box'],box)],key=lambda t:t['core'][1]if box[3]>box[2]else t['core'][0])
  if 2<=len(inner)<=8 and len({t['core'][0]for t in inner})==1 and not all(t['hollow']for t in inner):groups.append(dict(box=box,color=color,tokens=inner))
 if not groups:return None
 rows=list(layouts(f).values());byrow=defaultdict(list)
 for t in ts:byrow[(t['core'][0],t['box'][2])].append(t)
 rows.extend(tuple(sorted(r,key=lambda t:t['core'][1]))for r in byrow.values()if len(r)>=3)
 goalrows=[r for r in rows if len(r)>=3 and all(t['hollow']for t in r)]
 if not goalrows:return None
 goal=max(goalrows,key=lambda r:(sum(t['box'][2]for t in r),len(r)));size=max(t['box'][2]for t in goal);goal=tuple(sorted([t for t in ts if t['hollow']and t['box'][2]==size],key=lambda t:t['core']));inks={t['color']for t in goal};palette_rows=[r for r in rows if len(r)>=3 and not any(t in goal for t in r)and not any(enclosed(t['box'],g['box'])for t in r for g in groups)]
 if not palette_rows:return None
 palette=max(palette_rows,key=lambda r:(len({t['color']for t in r}&inks),len(r)));groups=sorted(groups,key=lambda g:g['box']);bycolor={g['color']:i for i,g in enumerate(groups)}
 for g in groups:
  g['links']=[bycolor.get(ring_color(f,t))for t in g['tokens']]
 return dict(goal=goal,desired=[t['color']for t in goal],palette=palette,groups=groups,root=0)

def finite_synthesize(c,limit=60):
 gs=c['groups'];solid={t['color']for t in c['palette']if not t['hollow']};refs={t['color']for t in c['palette']if t['hollow']};calls=[0]
 def merge(a,b):
  if any(k in a and a[k]!=v for k,v in b.items()):return None
  return dict(a,**{})|b
 def group(i,seq,stack):
  if i in stack or len(seq)<len(gs[i]['tokens']):return []
  calls[0]+=1
  if calls[0]>50000:return []
  g=gs[i];out=[]
  def walk(slot,pos,assign):
   if len(out)>=limit:return
   if slot==len(g['tokens']):
    if pos==len(seq):out.append(assign)
    return
   if pos>=len(seq):return
   t=g['tokens'][slot];fixed=g['links'][slot];v=seq[pos]
   if fixed is None and(v in solid or not t['hollow']and t['color']==v):walk(slot+1,pos+1,assign|{(i,slot):('literal',v)})
   children=[fixed]if fixed is not None else[j for j,z in enumerate(gs)if z['color']in refs and j!=i]
   for child in children:
    if child in stack or child==i:continue
    maxlen=len(seq)-pos-(len(g['tokens'])-slot-1)
    for n in range(len(gs[child]['tokens']),maxlen+1):
     for sub in group(child,seq[pos:pos+n],stack+(i,)):
      merged=merge(assign,sub)
      if merged is not None:walk(slot+1,pos+n,merged|{(i,slot):('reference',gs[child]['color'])})
  walk(0,0,{})
  return out
 options=group(c['root'],c['desired'],())
 def cost(a):
  return sum(not(kind=='reference'and gs[i]['links'][k]is not None and gs[gs[i]['links'][k]]['color']==ink or kind=='literal'and not gs[i]['tokens'][k]['hollow']and gs[i]['tokens'][k]['color']==ink)for(i,k),(kind,ink)in a.items())
 available=Counter((('reference'if t['hollow']else'literal'),t['color'])for t in c['palette'])
 def feasible(a):
  needed=Counter()
  for(i,k),(kind,ink)in a.items():
   t=gs[i]['tokens'][k];fixed=gs[i]['links'][k]
   fulfilled=(kind=='reference'and fixed is not None and gs[fixed]['color']==ink)or(kind=='literal'and not t['hollow']and t['color']==ink)
   if not fulfilled:needed[kind,ink]+=1
  return all(v<=available[k]for k,v in needed.items())
 options=[a for a in options if feasible(a)]
 if not options:return None
 a=min(options,key=lambda a:(cost(a),sorted(a.items())));return dict(assignments=[dict(group=i,slot=k,kind=v[0],ink=v[1])for(i,k),v in sorted(a.items(),key=lambda q:(-q[0][0],q[0][1]))],search_calls=calls[0],alternatives=len(options),hypothesis='ordered_expansion_of_visible_group_references_matches_goal_row')


def recursive_synthesize(c):
 gs=c['groups'];want=c['desired'];available=Counter((('reference'if t['hollow']else'literal'),t['color'])for t in c['palette']);bycolor={g['color']:i for i,g in enumerate(gs)};calls=[0]
 def solve(stack,pos,assign,remaining,seen):
  calls[0]+=1
  if calls[0]>100000 or len(stack)>len(want)*4+8:return None
  if pos==len(want):
   if all((i,j)in assign for i,g in enumerate(gs)for j in range(len(g['tokens']))):return assign
   return None
  if not stack:return None
  i,j=stack[-1]
  if j==len(gs[i]['tokens']):return solve(stack[:-1],pos,assign,remaining,seen)
  signature=(pos,i,j,tuple(sorted(assign.items())))
  if signature in seen:return None
  seen=seen|{signature};t=gs[i]['tokens'][j];fixed=gs[i]['links'][j];options=[]
  if(i,j)in assign:options=[(assign[i,j],False)]
  elif fixed is not None:options=[(('reference',gs[fixed]['color']),False)]
  else:
   v=want[pos]
   if not t['hollow']and t['color']==v:options.append((('literal',v),False))
   elif remaining['literal',v]>0:options.append((('literal',v),True))
   options.extend((('reference',ink),True)for ink in sorted(bycolor)if remaining['reference',ink]>0)
  for value,consume in options:
   kind,ink=value;a=assign|{(i,j):value};r=remaining.copy()
   if consume:r[value]-=1
   rest=stack[:-1]+((i,j+1),)
   if kind=='literal':
    if ink!=want[pos]:continue
    result=solve(rest,pos+1,a,r,seen)
   else:result=solve(rest+((bycolor[ink],0),),pos,a,r,seen)
   if result is not None:return result
  return None
 a=solve(((c['root'],0),),0,{},available,set())
 if a is None:return None
 return dict(assignments=[dict(group=i,slot=j,kind=v[0],ink=v[1])for(i,j),v in sorted(a.items(),key=lambda q:(-q[0][0],q[0][1]))],search_calls=calls[0],alternatives=1,hypothesis='bounded_recursive_expansion_matches_visible_goal_prefix')

def synthesize(c,limit=60):
 return finite_synthesize(c,limit)or recursive_synthesize(c)
