"""Visible shapes with isolated control marks filled; mode identifies the selected object."""
from collections import Counter
from modal_visible_parts_v1 import parts
from modal_eight_parts_v1 import parts as eight_parts

def clean(frame):
 f=[row[:]for row in frame]
 for p in parts(frame):
  if p['area']!=1:continue
  y,x=p['y'],p['x']
  if 0<y<63 and 0<x<63:
   ns=[frame[y-1][x],frame[y+1][x],frame[y][x-1],frame[y][x+1]]
   if len(set(ns))==1:f[y][x]=ns[0]
 return f

def key(p):return(p['color'],p['h'],p['w'],tuple(map(tuple,p['shape'])))
def shape(p):return tuple(map(tuple,p['shape']))
def board(frame):
 f=clean(frame);bottom=max(Counter(frame[-1]).values())>=.9*len(frame[-1]);right=max(Counter(row[-1]for row in frame).values())>=.9*len(frame)
 return[row[:-1]if right else row for row in(f[:-1]if bottom else f)]
def objects(o):return[p for p in eight_parts(board(o['frame']))if p['area']>=9 and p['h']>2 and p['w']>2 and p['area']<1024]
def context(o,marker):
 f=o['frame'];ps=parts(f);hosts=Counter()
 for p in ps:
  if p['area']!=1 or p['color']!=marker:continue
  y,x=p['y'],p['x']
  if not(0<y<63 and 0<x<63):continue
  ns=[f[y-1][x],f[y+1][x],f[y][x-1],f[y][x+1]]
  if len(set(ns))==1:hosts[ns[0]]+=1
 if not hosts:
  for p in ps:
   if p['area']==1 and p['color']==marker:
    y,x=p['y'],p['x']
    for q in objects(o):
     if q['y']<=y<q['y']+q['h']and q['x']<=x<q['x']+q['w']and q['color']!=marker:hosts[q['color']]+=1
 if not hosts:return('unknown',)
 ink=hosts.most_common(1)[0][0];points=[(y,x)for y,row in enumerate(f)for x,c in enumerate(row)if c==ink]
 if points:
  hh=max(y for y,x in points)-min(y for y,x in points)+1;ww=max(x for y,x in points)-min(x for y,x in points)+1
  if(hh>50 and ww<=4)or(ww>50 and hh<=4):return(ink,'axis')
 from reflection_axes_v4 import axes
 for a in axes(o):
  if a['ink']!=ink:continue
  if a['axis']=='both':
   hr=sum(p['color']==marker and p['area']==1 and abs(p['y']-a['center_y'])<=1 for p in ps);vr=sum(p['color']==marker and p['area']==1 and abs(p['x']-a['center_x'])<=1 for p in ps)
   return(ink,'axis','horizontal'if hr>=vr else'vertical')
  return(ink,'axis')
 candidates=[]
 for p in objects(o):
  if p['color']!=ink:continue
  n=sum(1 for q in ps if q['color']==marker and q['area']==1 and p['y']<=q['y']<p['y']+p['h']and p['x']<=q['x']<p['x']+p['w'])
  if n:candidates.append((n,p))
 if not candidates:return(ink,'axis')
 p=max(candidates,key=lambda q:q[0])[1]
 if p['h']>30 or p['w']>30:return(ink,'axis')
 return(ink,p['h'],p['w'],shape(p))

def marker_ink(o):
 ps=parts(o['frame']);singles=Counter(p['color']for p in ps if p['area']==1);counts=Counter(v for row in o['frame']for v in row)
 return min((c for c,n in singles.items()if n>=3),key=lambda c:counts[c])
