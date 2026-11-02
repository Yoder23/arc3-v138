"""Plan visible upward clearance, then test tile removal and sustained motion."""
import copy
from collections import Counter
from corridor_motion_inquiry_v3 import Agent as Tracker
from structured_interaction_probe_v1 import parts
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.tracker=Tracker();self.previous=None;self.last=None;self.effects=[];self.steps=0;self.resets=0;self.direction=4;self.free_color=None;self.free_source=None;self.blocked={};self.barriers={};self.failed={};self.transitions=[];self.refuted={}
 def respond(self,obs):
  actor=self.tracker.actor(obs);ps=parts(obs['frame']);a=None;data={};c=None;reason='unresolved_clearance';columns=[];tile=None
  if self.previous is not None:
   e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(obs));self.effects.append(dict(source=digest(e),progress=obs['levels_completed']>self.previous['levels_completed'] or obs['state']=='WIN'))
  if self.previous is not None:
   self.transitions.append(dict(source=self.effects[-1]['source'],before=digest([self.previous['levels_completed'],self.previous['frame'][:62]]),after=digest([obs['levels_completed'],obs['frame'][:62]]),action=self.last['action'],data=self.last['data']))
  if obs['state']=='GAME_OVER' and self.previous is not None:
   failure_context=digest([self.previous['levels_completed'],self.previous['frame'][:62]]);self.failed[(failure_context,self.last['action'],tuple(sorted(self.last['data'].items())))]=self.effects[-1]['source']
  if self.previous is not None and self.last['action'] in (3,4):
   old=self.tracker.actor(self.previous)
   if old and actor and old['x']==actor['x'] and old['y']==actor['y']:
    self.direction=7-self.direction;ctx=digest([obs['levels_completed'],actor['y'],actor['x'],[row[max(0,actor['x']-6):min(64,actor['x']+8)] for row in obs['frame'][max(0,actor['y']-6):actor['y']]]]);self.blocked[(ctx,self.last['action'])]=self.effects[-1]['source'];board=digest([obs['levels_completed'],obs['frame'][:max(0,actor['y']-6)]]);self.barriers[(board,actor['x']+actor['w']//2,self.last['action'])]=self.effects[-1]['source']
  if obs['state']=='GAME_OVER' and self.resets<8:self.resets+=1;a=0;reason='retain_observations_and_retry'
  elif actor and obs['state']=='NOT_FINISHED' and self.steps<240:
   y=actor['y']+actor['h']//2;x=actor['x']+actor['w']//2;near=[p for p in ps if p['area']<=3 and p['color']!=actor['color'] and p['y']>=actor['y'] and p['y']+p['h']<=actor['y']+actor['h'] and min(abs(p['x']+p['w']-actor['x']),abs(p['x']-actor['x']-actor['w']))==0]
   if len(near)==1:p=near[0];x=(min(actor['x'],p['x'])+max(actor['x']+actor['w']-1,p['x']+p['w']-1))//2
   f=obs['frame'];free=Counter(f[yy][xx] for yy in range(y,min(y+7,62)) for xx in range(max(x-4,0),min(x+5,64)) if f[yy][xx]!=actor['color']).most_common(1)[0][0];fresh_free=free
   if self.free_color is None:self.free_color=free;self.free_source=digest(obs)
   free=self.free_color;tiles=[p for p in ps if 3<=p['h']<=7 and 3<=p['w']<=7 and p['area']>=16];groups=Counter((p['h'],p['w'],p['shape']) for p in tiles);signature=groups.most_common(1)[0][0] if groups else None;tiles=[p for p in tiles if (p['h'],p['w'],p['shape'])==signature]
   covered={(yy,xx) for p in tiles for yy in range(max(0,p['y']-1),min(62,p['y']+p['h']+1)) for xx in range(max(0,p['x']-1),min(64,p['x']+p['w']+1))};step=6
   ctx=digest([obs['levels_completed'],actor['y'],actor['x'],[row[max(0,actor['x']-6):min(64,actor['x']+8)] for row in f[max(0,actor['y']-6):actor['y']]]]);blocked_dirs={a for (k,a) in self.blocked if k==ctx}
   board=digest([obs['levels_completed'],f[:max(0,actor['y']-6)]]);walls=[(at,a) for (key,at,a) in self.barriers if key==board]
   for xx in range(x%step,64,step):
    if any((a==4 and x<=at<xx) or (a==3 and xx<at<=x) for at,a in walls):continue
    if (xx<x and 3 in blocked_dirs) or (xx>x and 4 in blocked_dirs):continue
    if f[y][xx] not in (free,actor['color']) and (y,xx) not in covered and abs(xx-x)>2:continue
    top=y
    for yy in range(y-1,-1,-1):
     if f[yy][xx] in (free,actor['color']) or (yy,xx) in covered:top=yy
     else:break
    columns.append(dict(x=xx,top=top))
   if columns:
    best=min(columns,key=lambda p:(p['top'],abs(p['x']-x)));target=best['x'];blockers=[p for p in tiles if p['x']<=target<p['x']+p['w'] and best['top']<=p['y']<y]
    if abs(target-x)>=step:
     nextx=x+(step if target>x else -step);tile=next((p for p in tiles if p['x']-1<=nextx<=p['x']+p['w'] and p['y']-1<=y<=p['y']+p['h']),None)
     if tile:a=6;data=dict(y=tile['y']+tile['h']//2,x=tile['x']+tile['w']//2);reason='remove_tile_before_lateral_relocation'
     else:a=4 if target>x else 3;self.direction=a;reason='move_toward_visible_upward_clearance'
    elif blockers:
     tile=max(blockers,key=lambda p:p['y']);a=6;data=dict(y=tile['y']+tile['h']//2,x=tile['x']+tile['w']//2);reason='remove_observed_tile_on_selected_route'
    else:
     alternatives=[p for p in columns if p['x']!=x and abs(p['x']-x)==step];bestnext=min(alternatives,key=lambda p:(p['top'],p['x'])) if alternatives else None
     a=self.direction if self.direction not in blocked_dirs else (7-self.direction if 7-self.direction not in blocked_dirs else None);reason='test_alternative_after_retained_blockage'
   failure_context=digest([obs['levels_completed'],obs['frame'][:62]])
   rejected=set(self.failed)|set(self.refuted)
   if (failure_context,a,tuple(sorted(data.items()))) in rejected:
    alternatives=[v for v in (self.direction,7-self.direction) if v in obs['available_actions'] and (failure_context,v,()) not in rejected and v!=a]
    if alternatives:a=alternatives[0];data={};tile=None;self.direction=a;reason='test_alternative_to_retained_terminal_failure'
    elif self.transitions and self.resets<8:
     entry=self.transitions[-1];self.refuted[(entry['before'],entry['action'],tuple(sorted(entry['data'].items())))]=dict(source=entry['source'],failed_continuations=[dict(action=v,source=self.failed.get((failure_context,v,()))) for v in (3,4)],interpretation='revise_entry_approach_after_tested_continuations_failed');a=0;data={};tile=None;self.resets+=1;reason='retain_failed_branch_and_try_an_earlier_alternative'
    else:a=None;data={};tile=None;reason='terminal_failure_alternatives_exhausted'
   if a is not None:c=dict(kind='clearance_route_inquiry',context=digest(obs),action=a,actor=actor,columns=columns,free_color=free,free_color_source=self.free_source,retained_blockages=[dict(context=k,action=a,source=v) for (k,a),v in self.blocked.items()],retained_barriers=[dict(context=k,at=at,action=a,source=v) for (k,at,a),v in self.barriers.items()],tile=tile,effects=copy.deepcopy(self.effects),terminal_failures=[dict(context=k,action=a,data=dict(d),source=v) for (k,a,d),v in self.failed.items()],refuted_approaches=[dict(context=k,action=a,data=dict(d),proof=v) for (k,a,d),v in self.refuted.items()],goal_is_hypothesis=True)
  if a is not None:self.steps+=1
  r=dict(action=a,data=data,done=a is None,certificate=c,advisor='clearance_route_inquiry',diagnostics=dict(reason=reason,steps=self.steps,resets=self.resets));self.previous=copy.deepcopy(obs);self.last=copy.deepcopy(r);return r
