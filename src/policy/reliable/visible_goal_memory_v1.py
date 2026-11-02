import copy
def visible(frame):
 goals={}
 for y in range(1,min(61,len(frame)-1)):
  for x in range(1,len(frame[y])-1):
   c=frame[y][x]
   if c in (4,5,0):continue
   if all(frame[y+a][x+b]==4 for a in (-1,0,1) for b in (-1,0,1) if a or b):goals.setdefault(c,[]).append((y,x))
 return goals
def merge(targets,new):
 out={int(k):list(map(tuple,v)) for k,v in targets.items()}
 for c,ps in new.items():out[int(c)]=sorted(set(out.get(int(c),[]))|set(map(tuple,ps)))
 return out
def scene(initial,targets):
 out=copy.deepcopy(initial);out['targets']=copy.deepcopy(targets);return out
