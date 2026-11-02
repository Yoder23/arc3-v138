"""Track the task actor while excluding its previously observed goal display."""
from binary_animation_learning_v8 import components

def track(frame,pairs,scene):
 if not pairs or not scene:return None
 top=min(a['box'][0]for a,b in pairs);lo=max(0,min(a['box'][1]for a,b in pairs)-8);hi=min(64,max(a['box'][1]for a,b in pairs)+10)
 gy,gx,gh,gw=scene['goal']['box'];floor=set(scene['floor_inks'])
 found=[]
 for obj in components(frame):
  y,x,h,w=obj['box']
  if not(lo<=x<hi and y+h<top and 3<=h==w<=24 and .75<=len(obj['shape'])/(h*w)<1 and obj['ink']not in floor):continue
  if not(y+h<=gy or gy+gh<=y or x+w<=gx or gx+gw<=x):continue
  found.append(obj)
 if len(found)==1:return found[0]
 # Components can merge with a marked floor tile. Preserve the observed sprite
 # mask and abstain unless one literal location fits outside the goal display.
 model=scene['actor'];h,w=model['box'][2:];ink=model['ink'];shape=set(map(tuple,model['shape']));motifs=[]
 for y in range(max(0,top-h)):
  for x in range(lo,min(hi,65-w)):
   if not(y+h<=gy or gy+gh<=y or x+w<=gx or gx+gw<=x):continue
   if all((frame[y+dy][x+dx]==ink)==((dy,dx)in shape)for dy in range(h)for dx in range(w)):
    motifs.append(dict(box=(y,x,h,w),ink=ink,shape=sorted(shape)))
 return motifs[0]if len(motifs)==1 else None
