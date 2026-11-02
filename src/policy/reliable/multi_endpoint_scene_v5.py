"""Observe separately controlled rods, attached rectangular panels and every visible endpoint."""
from collections import Counter
from rope_visible_parts_v1 import parts

def key(p):return str(p['color'])+':'+str(tuple(map(tuple,p['shape'])))
def scene(o,templates=None,roles=None):
 ps=parts(o['frame']);f=o['frame'];bg=Counter(v for row in f for v in row).most_common(1)[0][0];buttons=[p for p in ps if p['h']==p['w']==3 and p['area']==7];colors=sorted({p['color'] for p in buttons});bodies=[];ends=[];marker=None
 for color in colors:
  cs=[p for p in ps if p['color']==color and p not in buttons and (p['h']==3 or p['w']==3) and p['area']>=5]
  if len(cs)!=1:return None
  p=cs[0]
  if roles:
   coords=[(q['y']+y,q['x']+x) for q in ps if q['color']==color and q['y']<44 for y,x in q['shape'] if (p['y']<=q['y']+y<p['y']+3 if p['h']==3 else p['x']<=q['x']+x<p['x']+3)]
   top=min(y for y,x in coords);left=min(x for y,x in coords);bottom=max(y for y,x in coords);right=max(x for y,x in coords);p=dict(color=color,y=top,x=left,h=bottom-top+1,w=right-left+1,area=len(coords),shape=tuple((y-top,x-left) for y,x in sorted(coords)))
  holes=[(y,x,f[y][x]) for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w']) if f[y][x]!=color]
  if roles:
   marker=roles['marker'];mask={(gy+dy,gx+dx) for gy,gx in roles['goals'] for dy,dx in [(0,0),(-1,0),(1,0),(0,-1),(0,1)]}
   if len([z for z in holes if z[:2] not in mask])>1:return None
  else:
   if len(holes)>1:return None
   if holes:ends.append(dict(color=color,point=list(holes[0][:2]),marker=holes[0][2]));marker=holes[0][2]
  roots=[]
  for q in ps:
   if q['area']!=3 or q['color']==color:continue
   if q['h']==3 and q['w']==1 and p['h']==3 and q['y']==p['y']:
    if q['x']+1==p['x']:roots.append([-1,0])
    elif p['x']+p['w']==q['x']:roots.append([1,0])
   if q['h']==1 and q['w']==3 and p['w']==3 and q['x']==p['x']:
    if q['y']+1==p['y']:roots.append([0,-1])
    elif p['y']+p['h']==q['y']:roots.append([0,1])
  if len(roots)!=1:return None
  bodies.append(dict(color=color,part=p,root=roots[0]))
  if roles and color in roles['end_colors']:
   rx,ry=roots[0]
   endpoint=[p['y']+1,p['x']+p['w']-2] if rx<0 else ([p['y']+1,p['x']+1] if rx>0 else ([p['y']+p['h']-2,p['x']+1] if ry<0 else [p['y']+1,p['x']+1]))
   if f[endpoint[0]][endpoint[1]]!=marker:return None
   ends.append(dict(color=color,point=endpoint,marker=marker))
 if len(ends)<2:return None
 goals=[[y,x] for y in range(1,44) for x in range(1,63) if all(f[y+a][x+b]==marker for a,b in [(-1,0),(1,0),(0,-1),(0,1)])]
 panels=[]
 for color in sorted({p['color'] for p in ps if p['y']<44 and p['color'] not in colors+[marker,bg] and p['area']>=20}):
  for axis in (0,1):
   hits=[]
   for cross in range(1,44 if axis==0 else 63):
    line=[j for j in range(1,63 if axis==0 else 44) if (f[cross][j] if axis==0 else f[j][cross])==color];runs=[]
    for j in line:
     if runs and j==runs[-1][-1]+1:runs[-1].append(j)
     else:runs.append([j])
    for run in runs:
     if len(run)>=8:hits.append((cross,run[0],len(run)))
   for cross,start,length in hits:
    if (cross-1,start,length) in hits or not all((cross+k,start,length) in hits for k in (1,2)):continue
    if (cross+3,start,length) in hits:continue
    y,x,h,ww=(cross,start,3,length) if axis==0 else (start,cross,length,3);panels.append(dict(color=color,axis=axis,y=y,x=x,h=h,w=ww))
 panels.sort(key=lambda p:(p['color'],p['axis'],p['y'],p['x']))
 if templates is None:
  templates=[]
  for p in panels:
   candidates=[]
   for b in bodies:
    z=b['part']
    if p['axis']==0 and z['w']==3 and z['y']==p['y']+3 and z['x']==p['x']:candidates.append(b)
    if p['axis']==1 and z['h']==3 and z['x']==p['x']+3 and z['y']==p['y']:candidates.append(b)
   if len(candidates)!=1:return None
   b=candidates[0];templates.append(dict(color=p['color'],axis=p['axis'],h=p['h'],w=p['w'],body=b['color'],dy=p['y']-b['part']['y'],dx=p['x']-b['part']['x']))
 panels=[]
 for t in templates:
  b=next((b for b in bodies if b['color']==t['body']),None)
  if not b:return None
  p=dict(color=t['color'],axis=t['axis'],y=b['part']['y']+t['dy'],x=b['part']['x']+t['dx'],h=t['h'],w=t['w'])
  if not all(0<=y<64 and 0<=x<64 and (f[y][x]==p['color'] or any(abs(y-gy)+abs(x-gx)<=1 for gy,gx in goals)) for y in range(p['y'],p['y']+p['h']) for x in range(p['x'],p['x']+p['w'])):return None
  panels.append(p)
 walls=[]
 for p in ps:
  if p['y']<44 and p['h']==p['w']==3 and p['area']==9 and p['color'] not in colors+[marker,bg]:walls.extend((p['y']+y,p['x']+x) for y,x in p['shape'])
 state=tuple(v for b in bodies for v in [b['part'][k] for k in ['y','x','h','w']])+tuple(v for p in panels for v in [p[k] for k in ['y','x','h','w']])+tuple(v for e in ends for v in e['point'])
 return dict(bodies=bodies,buttons=buttons,ends=ends,goals=goals,panels=panels,templates=templates,roles=dict(marker=marker,goals=goals,end_colors=[e['color'] for e in ends]),walls=walls,state=state)

def valid(s,sc):
 wall=set(map(tuple,sc['walls']));rects=[]
 for i,b in enumerate(sc['bodies']):
  y,x,h,w=s[4*i:4*i+4]
  if min(h,w)<2 or y<1 or x<1 or y+h>=44 or x+w>=63 or (h!=3 and w!=3):return False
  pix={(yy,xx) for yy in range(y,y+h) for xx in range(x,x+w)};rx,ry=b['root']
  if rx:pix|={(yy,x-1 if rx<0 else x+w) for yy in range(y,y+h)}
  if ry:pix|={(y-1 if ry<0 else y+h,xx) for xx in range(x,x+w)}
  if pix&wall:return False
  rects.append(pix)
 offset=4*len(sc['bodies'])
 for j,p in enumerate(sc['panels']):
  y,x,h,w=s[offset+4*j:offset+4*j+4]
  if y<1 or x<1 or y+h>=44 or x+w>=63:return False
  pix={(yy,xx) for yy in range(y,y+h) for xx in range(x,x+w)}
  if pix&wall:return False
  rects.append(pix)
 for i,a in enumerate(rects):
  if any(a&b for b in rects[i+1:]):return False
 return True
