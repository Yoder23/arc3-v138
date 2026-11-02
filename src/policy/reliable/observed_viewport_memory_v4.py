from collections import Counter
from observed_viewport_memory_v3 import infer as prior
from retained_peg_scene_v1 import scene
from matrix_motion_learner_v6 import objects

def alignment(before,after,dy,dx,mb,ma):
 bg=Counter(v for row in before[3:]for v in row).most_common(1)[0][0];same=total=0
 def inside(y,x,boxes):return any(b['box'][0]<=y<b['box'][0]+b['box'][2]and b['box'][1]<=x<b['box'][1]+b['box'][3]for b in boxes)
 for y in range(max(3,3+dy),min(64,64+dy)):
  for x in range(max(0,dx),min(64,64+dx)):
   if inside(y,x,mb)or inside(y-dy,x-dx,ma):continue
   a=before[y][x];b=after[y-dy][x-dx]
   if a==bg and b==bg:continue
   total+=1;same+=a==b
 return same,total

def infer(before,after,template=None,dynamic_ink=None):
 result=prior(before,after,template)
 if result['supported']or dynamic_ink is None:return result
 a=scene(before,template);b=scene(after,a or template)
 if not a or not b:return result
 masks=[]
 for f in [before,after]:masks.append([o for o in objects(f)if not o.get('parts')and o['ink']==dynamic_ink and o['box'][2]==o['box'][3]==a['size']+2])
 if not all(masks)or any(len(v)>8 for v in masks):return result
 shifts=Counter((y-yy,x-xx)for y,x in a['cells']for yy,xx in b['cells']);rank=[]
 for d in {(0,0)}|{d for d,n in shifts.items()if n>=4}:
  same,total=alignment(before,after,*d,*masks)
  if total>=120:rank.append((same/total,d,same,total))
 rank.sort(reverse=True)
 if not rank:return result
 best=rank[0];zero=next((r[0]for r in rank if r[1]==(0,0)),0.);second=rank[1][0]if len(rank)>1 else 0.
 supported=best[1]!=(0,0)and best[0]>=.8 and best[0]-zero>=.1 and best[0]-second>=.04
 if not supported:return result
 return dict(delta=best[1],supported=True,agreement=best[0],unshifted_agreement=zero,runner_up=second,matched=best[2],compared=best[3],registration_masks=dict(before=masks[0],after=masks[1],ink=dynamic_ink),hypothesis='register_static_terrain_after_excluding_observed_carrier_bodies')
