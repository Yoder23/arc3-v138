"""Treat an observed failed goal entry as conditional on the carried symbol."""
def regions(scene,barriers,contacts,level):
 done={tuple(r['goal'])for r in contacts if r['level']==level}
 wanted={tuple(r['goal'])for r in barriers if r['level']==level}-done
 return [dict(g)for g in scene.get('goal_options',[])if tuple(g['box'])in wanted]
def covers(p,n,g):
 y,x,h,w=g['box'];return p[0]<=y+h//2<p[0]+n and p[1]<=x+w//2<p[1]+n
def relaxed(motion,goals):
 out=dict(motion)
 for (p,action,n),q in list(out.items()):
  dy,dx={1:(-1,0),2:(1,0),3:(0,-1),4:(0,1)}[action];dest=(p[0]+dy*n,p[1]+dx*n)
  if q==p and any(covers(dest,n,g)for g in goals):out.pop((p,action,n))
 return out
def resolve(motion,p,action,n,key,color,goals):
 dy,dx={1:(-1,0),2:(1,0),3:(0,-1),4:(0,1)}[action];dest=(p[0]+dy*n,p[1]+dx*n)
 q=motion.get((p,action,n),dest)
 for g in goals:
  if covers(dest,n,g)and not covers(p,n,g):
   matches=tuple(map(tuple,key))==tuple(map(tuple,g['glyph']))and color==g['color']
   return dest if matches else p
 return q
