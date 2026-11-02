"""Preserve previously observed rectangle boundaries when selection colors merge."""
def recover(scene,old,frame):
 if not scene or not old or len(scene['bars'])>=len(old['bars']):return scene
 inks={b['ink']for b in old['bars']}|{b['ink']for b in scene['bars']};bars=[]
 for b in old['bars']:
  y,x,h,w=b['box'];colors={frame[yy][xx]for yy in range(y,y+h)for xx in range(x,x+w)}
  if len(colors)!=1 or next(iter(colors))not in inks:return scene
  bars.append(dict(b,ink=next(iter(colors)),box=tuple(b['box'])))
 return dict(scene,bars=bars)
