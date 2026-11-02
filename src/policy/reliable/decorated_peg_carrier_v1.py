from matrix_motion_learner_v6 import objects

def motif(frame,y,x,rule):
 n=rule['size'];pattern=[row[1:n+1]for row in rule['patch'][:n]]
 return y>=1 and x>=0 and y+n-1<=64 and x+n<=64 and [row[x:x+n]for row in frame[y-1:y+n-1]]==[list(row)for row in pattern]
def carriers(frame,template,rules):
 if not template:return []
 n=template['body']['box'][2];ink=template['body']['ink'];out=[]
 expected={(dy,dx)for dy in range(n)for dx in range(n)if dy in(0,n-1)or dx in(0,n-1)}
 for o in objects(frame):
  if o.get('parts')or o['ink']!=ink or o['box'][2:]!=(n,n):continue
  shape=set(o['shape']);y,x,_,_=o['box']
  if not(shape<expected and len(shape)>=3*n-2):continue
  if expected-shape!={(0,x)for x in range(1,n-1)}:continue
  for r in rules:
   if motif(frame,y+1,x+1,r):out.append(dict(o,decorated_template_source=template['source'],pivot_rule_source=r['source']));break
 return out
