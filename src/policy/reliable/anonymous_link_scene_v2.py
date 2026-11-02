"""Pixel-supported endpoint motifs remain recognizable when touching a goal ring."""
import itertools
from collections import Counter
from anonymous_link_inquiry_v2 import BODY,parse as prior_parse
END=[(a,b) for a in range(-2,3) for b in range(-2,3) if 0<abs(a)+abs(b)<=2]
def parse(obs,expected=()):
 f=obs['frame'];bg=Counter(v for row in f for v in row).most_common(1)[0][0];ends=[];_,pads,_=prior_parse(obs)
 for y in range(2,62):
  for x in range(2,62):
   vals={f[y+a][x+b] for a,b in END}
   if len(vals)==1 and bg not in vals and f[y][x] not in vals and f[y][x]!=bg:ends.append(dict(color=next(iter(vals)),point=(y,x)))
 for old in expected:
  y,x=old['point']
  if any(o['point']==(y,x) for o in ends) or not(2<=y<62 and 2<=x<62):continue
  colors={o['color'] for o in ends}|{old['color']}
  support=[(sum(f[y+a][x+b]==c for a,b in END),c) for c in colors if c!=bg]
  if support and max(support)[0]>=8 and f[y][x]!=bg:ends.append(dict(color=max(support)[1],point=(y,x)))
 groups=[]
 for n in range(2,min(6,len(ends))+1):
  for subset in itertools.combinations(ends,n):
   center=tuple(sum(o['point'][i] for o in subset)//n for i in (0,1));y,x=center;vals={f[y+a][x+b] for a,b in BODY}
   if bg not in vals and len(vals)<=4:groups.append(dict(members=list(subset),center=center,signature=sorted(vals)))
 return ends,pads,groups
