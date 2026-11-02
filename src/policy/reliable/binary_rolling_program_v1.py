"""Replan observed translation programs across finite interface horizons."""
import copy
from collections import deque
from binary_animation_learning_v8 import Agent as Base,bit_groups,columns,target_scene,heading,components


def long_route(frame,scene,models,slots,blocked=()):
    a=scene['actor'];h,w=a['box'][2:];start=tuple(a['box'][:2]);goal=tuple(scene['target']);hd=heading(a)
    if tuple(scene['target_body']['box'][2:])!=(h,w)or scene['target_heading']!=hd or scene['target_ink']!=a['ink']:return None
    moves={};neutral=None
    for m in models.values():
        if m['before']['box'][2:]!=m['after']['box'][2:]or m['before']['ink']!=m['after']['ink']or m['heading_before']!=m['heading_after']:continue
        code=tuple(m['word']);delta=tuple(m['delta'])
        if delta==(0,0):neutral=code
        elif (delta[0]==0)!=(delta[1]==0):moves[code]=delta
    floor=set(scene['floor_inks'])|{a['ink']};goal_points={(scene['goal']['box'][0]+y,scene['goal']['box'][1]+x)for y,x in scene['goal']['shape']}
    todo=deque([start]);parents={start:None};blocked=set(blocked)
    while todo and goal not in parents and len(parents)<4096:
        y,x=todo.popleft()
        for word,(dy,dx)in sorted(moves.items()):
            q=y+dy,x+dx
            if q in parents or((y,x),word)in blocked or not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
            stride=max(abs(dy),abs(dx))
            if any(frame[y+dy*t//stride+iy][x+dx*t//stride+ix]not in floor and(y+dy*t//stride+iy,x+dx*t//stride+ix)not in goal_points for t in range(1,stride+1)for iy in range(h)for ix in range(w)):continue
            parents[q]=((y,x),word);todo.append(q)
    if goal not in parents:return None
    path=[];positions=[];q=goal
    while parents[q]:
        positions.append(q);q,word=parents[q];path.append(word)
    path.reverse();positions.reverse()
    if len(path)<slots:
        if neutral is None:return None
        padding=slots-len(path);path=[neutral]*padding+path;positions=[start]*padding+positions
    return dict(program=path[:slots],expected_position=positions[slots-1],whole_route=path,whole_route_positions=positions,start=start,target=goal)


class Agent(Base):
    def __init__(self,prior=None):
        super().__init__(prior);self.rolling=None;self.rolling_pending=None;self.execution_outcomes=[];self.blocked_steps=set();self.neutral_transfers=[]
    def respond(self,raw):
        if self.rolling_pending and raw['levels_completed']==self.rolling_pending['level']:
            p=self.rolling_pending;pairs=bit_groups(raw['frame'],self.bootstrap.values).get(self.main_background,[]);s=target_scene(raw['frame'],pairs)
            actual=tuple(s['actor']['box'][:2])if s else None
            matched=actual==tuple(p['expected_position']);self.execution_outcomes.append(dict(source=p['source'],level=p['level'],expected_position=p['expected_position'],actual_actor=copy.deepcopy(s['actor'])if s else None,matched=matched,program=p['program']))
            if matched:self.pending=None;self.plan=None
            elif s:
                frames=raw.get('animation_frames',[]);actors=[]
                for f in frames:
                    candidates=[o for o in components(f)if o['ink']==s['actor']['ink']and o['box'][2:]==s['actor']['box'][2:]and len(o['shape'])==len(s['actor']['shape'])]
                    actors.append(candidates[0]if len(candidates)==1 else None)
                if len(actors)==len(p['program'])+2:
                    for i,word in enumerate(p['program']):
                        if actors[i]and actors[i+1]and actors[i]['box'][:2]==actors[i+1]['box'][:2]and tuple(word)!=(0,)*len(word):self.blocked_steps.add((tuple(actors[i]['box'][:2]),tuple(word)))
            self.rolling_pending=None;self.rolling=None
        elif self.rolling_pending:
            self.rolling_pending=None;self.rolling=None;self.blocked_steps=set()
        result=super().respond(raw)
        if result['done']and raw['state']=='NOT_FINISHED'and self.models:
            pairs=bit_groups(raw['frame'],self.bootstrap.values).get(self.main_background,[]);cs=columns(pairs);s=target_scene(raw['frame'],pairs)
            if not cs or not s:return result
            for archive in self.model_archive:
                for m in archive['models']:
                    if tuple(m['word'])!=(0,)*len(cs[0])or m['before']!=m['after']:continue
                    key=(tuple(m['word']),tuple(m['before']['box'][2:]),m['heading_before'])
                    if key not in self.models:self.models[key]=copy.deepcopy(m);self.evidence.append(copy.deepcopy(m));self.neutral_transfers.append(dict(source=m['source'],from_level=archive['level'],to_level=self.learner_level))
            plan=long_route(raw['frame'],s,self.models,len(cs),self.blocked_steps)
            if plan:
                self.rolling=dict(source=self.t,level=self.learner_level,**plan);self.plan=plan['program'];result=super().respond(raw)
        if not result['done']:
            if self.rolling:
                result['certificate']['rolling_goal_plan']=copy.deepcopy(self.rolling)
                if result['certificate']['tag']=='test_observed_column_program':self.rolling_pending=dict(source=self.t-1,level=self.learner_level,program=self.plan,expected_position=self.rolling['expected_position'])
            if self.execution_outcomes:result['certificate']['intermediate_execution_outcomes']=copy.deepcopy(self.execution_outcomes)
            if self.neutral_transfers:result['certificate']['neutral_transfer_hypotheses']=copy.deepcopy(self.neutral_transfers)
        return result
