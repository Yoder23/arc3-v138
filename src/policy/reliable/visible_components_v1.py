"""Connected visible components, including those touching the frame boundary."""
import numpy as np
from scipy import ndimage
def parts(frame):
 a=np.asarray(frame);out=[]
 for color in sorted(set(a.ravel())):
  lab,_=ndimage.label(a==color)
  for j,box in enumerate(ndimage.find_objects(lab),1):
   if box is None:continue
   y,x=box[0].start,box[1].start;shape=tuple(map(tuple,np.argwhere(lab[box]==j).tolist()));out.append(dict(color=int(color),area=len(shape),y=y,x=x,h=box[0].stop-y,w=box[1].stop-x,shape=shape))
 return out
