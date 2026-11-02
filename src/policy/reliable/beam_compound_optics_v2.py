"""Compare separate and joined optical hypotheses using observed particle pixels."""
from beam_split_geometry_v9 import trace as separate_trace

def candidates(s,groups,frame):
 n=s['n'];axis=s['axis'];cross=1-axis;result=[]
 for group in groups:
  if len(group)<2:continue
  bars=[s['bars'][i]['box']for i in group]
  if len({(b[axis],b[axis+2])for b in bars})!=1:continue
  order=sorted(group,key=lambda i:s['bars'][i]['box'][cross]);bridges=[]
  for i,j in zip(order,order[1:]):
   a=s['bars'][i]['box'];b=s['bars'][j]['box'];start=a[cross]+a[cross+2];gap=b[cross]-start
   if gap!=n:break
   y,x=(a[0],start)if axis==0 else(start,a[1])
   inks={frame[yy][xx]for yy in range(y,y+n)for xx in range(x,x+n)}
   if len(inks)!=1 or next(iter(inks))in(s['background'],s['bars'][i]['ink'],s['bars'][j]['ink']):break
   bridges.append(dict(position=[y,x],ink=next(iter(inks))))
  else:result.append(dict(indices=list(order),bridges=bridges))
 return result

def compound_trace(s,poses):
 grouped={i for g in s.get('optical_groups',[])for i in g['indices']};bars=[];positions=[]
 for g in s.get('optical_groups',[]):
  boxes=[(*poses[i],*s['bars'][i]['box'][2:])for i in g['indices']]
  y=min(b[0]for b in boxes);x=min(b[1]for b in boxes);h=max(b[0]+b[2]for b in boxes)-y;w=max(b[1]+b[3]for b in boxes)-x
  bars.append(dict(box=(y,x,h,w)));positions.append((y,x))
 for i,b in enumerate(s['bars']):
  if i not in grouped:bars.append(b);positions.append(poses[i])
 return separate_trace(dict(s,bars=bars),positions)

def observed_tiles(s,raw):
 n=s['n'];ink=s['source']['object']['ink'];tiles=set()
 for frame in raw['animation_frames']:
  for y in range(s['origin'][0],64-n+1,n):
   for x in range(s['origin'][1],64-n+1,n):
    if all(frame[yy][xx]==ink for yy in range(y,y+n)for xx in range(x,x+n)):tiles.add((y,x))
 return tiles

def compare(s,groups,before,after):
 proposed=candidates(s,groups,before)
 if not proposed:return None
 poses=[b['box'][:2]for b in s['bars']];observed=observed_tiles(s,after);n=s['n']
 axis=s['axis'];direction=s['source']['direction'][axis];horizontal={b['box'][axis]-direction*n for b in s['bars']}
 domain={(y,x)for y in range(s['origin'][0],64-n+1,n)for x in range(s['origin'][1],64-n+1,n)if (y,x)[axis]not in horizontal and all(before[yy][xx]==s['background']for yy in range(y,y+n)for xx in range(x,x+n))}
 def error(prediction):
  points={tuple(p)for p in prediction['rays']if 0<=p[0]<=64-n and 0<=p[1]<=64-n and all(before[y][x]==s['background']for y in range(p[0],p[0]+n)for x in range(p[1],p[1]+n))}
  return sorted((points^observed)&domain)
 separate=error(separate_trace(s,poses));compound=error(compound_trace(dict(s,optical_groups=proposed),poses))
 return dict(groups=proposed,separate_unexplained=separate,compound_unexplained=compound,adopt=len(compound)<len(separate),interpretation='joined optical span is a revised hypothesis supported by fewer false particle predictions')
