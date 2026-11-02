"""Infer an attached emitter from a literal particle birth beside a moving joint."""
from beam_compound_optics_v2 import candidates
from beam_front_collision_v2 import trace as front_trace
def discover(s,groups,before,after):
 if not after.get('animation_frames'):return []
 n=s['n'];dy,dx=s['source']['direction'];ink=s['source']['object']['ink'];first=after['animation_frames'][0];result=[]
 for g in candidates(s,groups,before):
  for b in g['bridges']:
   y,x=b['position'];birth=(y+dy*n,x+dx*n)
   if not(0<=birth[0]<=64-n and 0<=birth[1]<=64-n):continue
   yy,xx=birth;cells=[(a,z)for a in range(yy,yy+n)for z in range(xx,xx+n)]
   if all(first[a][z]==ink for a,z in cells)and all(before[a][z]!=ink for a,z in cells):
    result.append(dict(group=g,bridge=b,birth=list(birth),direction=list(s['source']['direction']),particle_ink=ink))
 return result
def attach(s,groups,frame,rule):
 if not rule:return []
 n=s['n'];dy,dx=s['source']['direction'];result=[]
 for g in candidates(s,groups,frame):
  for b in g['bridges']:
   anchor=g['indices'][0];ay,ax=s['bars'][anchor]['box'][:2];y,x=b['position']
   result.append(dict(anchor=anchor,offset=[y+dy*n-ay,x+dx*n-ax],bridge=b,group=g['indices'],evidence_source=rule['source']))
 return result
def trace(s,poses):
 sources=list(s['sources'])
 for e in s.get('moving_emitters',[]):
  ay,ax=poses[e['anchor']];dy,dx=e['offset'];sources.append(dict(position=(ay+dy,ax+dx)))
 return front_trace(dict(s,sources=sources),poses)
