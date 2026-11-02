"""Object-relative descriptors for learned click preferences."""
from collections import Counter
import numpy as np
from scipy import ndimage
def describe_scene(frame):
 a=np.asarray(frame,dtype=np.int16);counts=Counter(map(int,a.ravel()));bg=min(counts,key=lambda c:(-counts[c],c))
 records=[];lookup=np.full(a.shape,-1,dtype=np.int32)
 for color in sorted(counts):
  if color==bg:continue
  labels,n=ndimage.label(a==color)
  for label,sl in enumerate(ndimage.find_objects(labels),1):
   if sl is None:continue
   mask=labels[sl]==label;h,w=mask.shape;size=int(mask.sum());rid=len(records)
   view=lookup[sl];view[mask]=rid
   records.append(dict(color=color,y=sl[0].start,x=sl[1].start,h=h,w=w,size=size,
    density=int(4*size/(h*w)),sym_y=int(np.array_equal(mask,mask[::-1])),sym_x=int(np.array_equal(mask,mask[:,::-1])),
    holes=int(np.any(ndimage.binary_fill_holes(mask)&~mask))))
 sizes=[r['size'] for r in records];populations=[n for c,n in counts.items() if c!=bg];components=Counter(r['color'] for r in records)
 for r in records:
  n=counts[r['color']]
  r['features']=(int(n==min(populations)),int(n==max(populations)),int(populations.count(n)==1),
   int(r['size']==min(sizes)),int(r['size']==max(sizes)),int(r['w']>r['h']),int(r['h']>r['w']),int(r['h']==r['w']),
   r['density'],r['sym_y'],r['sym_x'],r['holes'],min(3,components[r['color']]))
 return lookup,records
def descriptor(frame,action,scene=None):
 if action[0]!=6:return None
 x,y=action[1:]
 if not(0<=y<len(frame) and 0<=x<len(frame[0])):return None
 lookup,records=describe_scene(frame) if scene is None else scene
 index=int(lookup[y,x])
 if index<0:return None
 r=records[index]
 def zone(position,start,length):
  delta=2*(position-start)+1-length
  return 0 if abs(delta)<=max(1,length/3) else (1 if delta>0 else -1)
 return r['features']+(zone(x,r['x'],r['w']),zone(y,r['y'],r['h']))
