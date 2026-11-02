"""Recover literal rectangle identities after a measured one-cell move or selection."""
from beam_retained_segmentation_v1 import recover as static_recover
def recover(scene,old,frame,action=None,index=None,groups=None):
 if not scene or not old or len(scene['bars'])>=len(old['bars']):return scene
 n=old['n'];inks={b['ink']for b in old['bars']}|{b['ink']for b in scene['bars']};layouts=[]
 variants=[(0,0)]
 if action in(1,2,3,4)and index is not None:variants.append({1:(-n,0),2:(n,0),3:(0,-n),4:(0,n)}[action])
 moving=set(next((g for g in(groups or[])if index in g),[index]))
 for dy,dx in variants:
  bars=[];occupied=set();valid=True
  for i,b in enumerate(old['bars']):
   y,x,h,w=b['box'];y+=dy if i in moving else 0;x+=dx if i in moving else 0
   if not(0<=y<=64-h and 0<=x<=64-w):valid=False;break
   cells={(y+dy,x+dx)for dy,dx in b['shape']};colors={frame[yy][xx]for yy,xx in cells}
   if len(colors)!=1 or next(iter(colors))not in inks or occupied&cells:valid=False;break
   occupied|=cells;bars.append(dict(b,ink=next(iter(colors)),box=(y,x,h,w)))
  if valid:
   signature=tuple(b['box']for b in bars)
   if all(signature!=tuple(b['box']for b in q)for q in layouts):layouts.append(bars)
 return dict(scene,bars=layouts[0])if len(layouts)==1 else scene
