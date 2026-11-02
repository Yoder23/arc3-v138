"""Use visible connected wiring to disambiguate several same-colored portal pairs."""
from collections import defaultdict
def candidates(frame,s,parents,trials,route):
 n=s['actor']['box'][2];byink=defaultdict(list)
 for y in range(8,63-n):
  for x in range(1,63-n):
   ring=[frame[y-1][xx]for xx in range(x-1,x+n+1)]+[frame[y+n][xx]for xx in range(x-1,x+n+1)]+[frame[yy][x-1]for yy in range(y,y+n)]+[frame[yy][x+n]for yy in range(y,y+n)]
   if len(set(ring))!=1 or ring[0]in(s['floor'],s['outside'],s['actor']['ink']):continue
   occupied=tuple(s['actor']['box'][:2])==(y,x)
   if not all(frame[yy][xx]==s['floor']or(occupied and frame[yy][xx]==s['actor']['ink'])for yy in range(y,y+n)for xx in range(x,x+n)):continue
   byink[ring[0]].append((y,x))
 out=[]
 for ink,all_sites in byink.items():
  groups=[]
  if len(all_sites)==2:groups=[(all_sites,None)]
  elif len(all_sites)>2:
   unseen=set(all_sites)
   while unseen:
    site=min(unseen);origin=(site[0]-1,site[1]-1);seen={origin};todo=[origin]
    while todo:
     y,x=todo.pop()
     for yy,xx in((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
      if 0<=yy<64 and 0<=xx<64 and(yy,xx)not in seen and frame[yy][xx]==ink:seen.add((yy,xx));todo.append((yy,xx))
    members=sorted(q for q in unseen if(q[0]-1,q[1]-1)in seen);unseen-=set(members);groups.append((members,sorted(seen)))
  for sites,wiring in groups:
   if len(sites)!=2:continue
   for site in sites:
    if site in trials:continue
    follow=route(parents,site)
    if follow:
     proof=dict(ink=ink,sites=sites,role='paired_nonlocal_site_hypothesis')
     if wiring is not None:proof.update(connected_wiring=wiring,all_matching_sites=all_sites,role='connected_pair_nonlocal_site_hypothesis')
     out.append((len(follow),site,follow,proof))
 return sorted(out)
