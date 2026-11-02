"""Reassess collision hypotheses after observing an additional moving emitter."""
from beam_compound_optics_v2 import candidates,observed_tiles
from beam_moving_emitter_v1 import discover,attach
from beam_front_collision_v1 import trace as stopped_trace
from beam_front_collision_v2 import trace as redirected_trace
def trace(s,poses):
 sources=list(s['sources'])
 for q in s.get('moving_emitters',[]):
  y,x=poses[q['anchor']];dy,dx=q['offset'];sources.append(dict(position=(y+dy,x+dx)))
 return(stopped_trace if s.get('front_mode')=='stop'else redirected_trace)(dict(s,sources=sources),poses)
def compare(s,groups,before,after):
 births=discover(s,groups,before,after)
 if not births or after['state']!='NOT_FINISHED':return None
 poses=[b['box'][:2]for b in s['bars']];moving=attach(s,groups,before,dict(source=0));scene=dict(s,optical_groups=candidates(s,groups,before),moving_emitters=moving)
 n=s['n'];axis=s['axis'];d=s['source']['direction'][axis];skip={b['box'][axis]-d*n for b in s['bars']};actual=observed_tiles(s,after)
 domain={(y,x)for y in range(s['origin'][0],64-n+1,n)for x in range(s['origin'][1],64-n+1,n)if(y,x)[axis]not in skip and all(before[yy][xx]==s['background']for yy in range(y,y+n)for xx in range(x,x+n))}
 errors={mode:sorted(({tuple(p)for p in trace(dict(scene,front_mode=mode),poses)['rays']}^actual)&domain)for mode in('stop','redirect')}
 preference=min(errors,key=lambda k:(len(errors[k]),k))if len(errors['stop'])!=len(errors['redirect'])else None
 return dict(births=births,errors=errors,preference=preference,interpretation='compare complete joint optical, source and collision models against the same actual animation')
