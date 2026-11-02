"""Coordinate a tested portal approach with unfinished observed replay endpoints."""
def propose(s,moves,parents,recorded,anchor):
 if not anchor or not recorded:return None
 actual={tuple(o['box'][:2])for o in s['other_bodies']if o['box'][2:]==s['actor']['box'][2:]}
 pending=[p[-1]for p in recorded if p and tuple(p[-1]['position'])not in actual]
 if not pending:return None
 pos=tuple(s['actor']['box'][:2]);site=tuple(anchor['site']);neighbor=anchor.get('neighbor')
 if pos==site:
  choices=[]
  for q,link in parents.items():
   if link is None or tuple(link[0])!=pos:continue
   a=link[1];dy,dx=moves[a]
   if any(tuple(v)==(-dy,-dx)for v in moves.values()):choices.append((a,q))
  if not choices:return None
  action,neighbor=min(choices);anchor['neighbor']=neighbor
 elif neighbor is not None and pos==tuple(neighbor):
  link=parents.get(site)
  if link is None or tuple(link[0])!=pos:return None
  action=link[1]
 else:return None
 return dict(action=action,site=site,neighbor=neighbor,arrival_source=anchor['source'],pending_endpoints=pending,observed_bodies=sorted(actual),interpretation='test_portal_occupancy_when_a_recorded_helper_arrives')
