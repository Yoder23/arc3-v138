"""Revise a goal hypothesis after every perceived cup activates without progress."""
from beam_joint_model_selection_v1 import trace as joint_trace
def evidence(s,before,after):
 if before['levels_completed']!=after['levels_completed']or after['state']!='NOT_FINISHED'or not s.get('moving_emitters'):return None
 for t,frame in enumerate(after['animation_frames']):
  colors=[]
  for g in s['goals']:
   o=g['object'];y,x,h,w=o['box'];values={frame[y+dy][x+dx]for dy,dx in o['shape']}
   if len(values)!=1 or next(iter(values))in(o['ink'],s['background'],s['source']['object']['ink']):break
   colors.append(next(iter(values)))
  else:
   return dict(activation_frame=t,goal_colors=colors,joints=[q['bridge']for q in s['moving_emitters']],hypothesis='test_connecting_the_observed_internal_emitter_to_the_external_source_after_all_cups_activate_without_progress')
 return None
def trace(s,poses):
 result=joint_trace(s,poses)
 required=s.get('connected_source_goal',False)
 if required:
  external=joint_trace(dict(s,moving_emitters=[]),poses);rays={tuple(v)for v in external['rays']};n=s['n'];dy,dx=s['source']['direction'];marks=[]
  for q in s.get('moving_emitters',[]):
   y,x=poses[q['anchor']];oy,ox=q['offset'];marks.append((y+oy-dy*n,x+ox-dx*n))
  result=dict(result,joint_hits=[i for i,p in enumerate(marks)if p in rays],joint_targets=marks)
 return result
