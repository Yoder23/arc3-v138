"""Find long thin visual axes, including their occluded crossing."""
from collections import Counter

def axes(o):
 f=o['frame'];out=[]
 for ink in sorted({v for row in f for v in row}):
  rows=[y for y,row in enumerate(f)if sum(c==ink for c in row)>=30];cols=[x for x in range(64)if sum(row[x]==ink for row in f)>=30]
  def band(values):return bool(values)and len(values)>=2 and 2<=max(values)-min(values)+1<=5
  h,v=band(rows),band(cols)
  if h and v:out.append(dict(ink=ink,axis='both',center_y=(min(rows)+max(rows))/2,center_x=(min(cols)+max(cols))/2))
  elif h:out.append(dict(ink=ink,axis='horizontal',center=(min(rows)+max(rows))/2))
  elif v:out.append(dict(ink=ink,axis='vertical',center=(min(cols)+max(cols))/2))
 return out

def position(a):return(a['center_y'],a['center_x'])if a['axis']=='both'else(a['center'],0)
def target(a):return tuple(a['target_axis'])if a['axis']['axis']=='both'else(a['target_axis'],0)
