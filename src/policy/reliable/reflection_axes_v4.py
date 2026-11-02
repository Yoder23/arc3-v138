"""Find long thin visual axes, including their occluded crossing."""
from collections import Counter

def axes(o):
 raw=o['frame'];bottom=max(Counter(raw[-1]).values())>=.9*len(raw[-1]);right=max(Counter(row[-1]for row in raw).values())>=.9*len(raw);f=[row[:-1]if right else row for row in(raw[:-1]if bottom else raw)];out=[]
 for ink in sorted({v for row in f for v in row}):
  rows=[];cols=[]
  for y,row in enumerate(f):
   points=[x for x,c in enumerate(row)if c==ink]
   if len(points)>=12 and max(points)-min(points)>=.85*(len(row)-1):rows.append(y)
  for x in range(len(f[0])):
   points=[y for y,row in enumerate(f)if row[x]==ink]
   if len(points)>=12 and max(points)-min(points)>=.85*(len(f)-1):cols.append(x)
  def band(values):return bool(values)and len(values)>=2 and 2<=max(values)-min(values)+1<=5
  h,v=band(rows),band(cols)
  if h and v:out.append(dict(ink=ink,axis='both',center_y=(min(rows)+max(rows))/2,center_x=(min(cols)+max(cols))/2))
  elif h:out.append(dict(ink=ink,axis='horizontal',center=(min(rows)+max(rows))/2))
  elif v:out.append(dict(ink=ink,axis='vertical',center=(min(cols)+max(cols))/2))
 return out

def position(a):return(a['center_y'],a['center_x'])if a['axis']=='both'else(a['center'],0)
def target(a):return tuple(a['target_axis'])if a['axis']['axis']=='both'else(a['target_axis'],0)
