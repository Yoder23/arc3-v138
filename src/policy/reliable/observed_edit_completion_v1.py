"""Confirm proposed local edits before issuing the dependent operation.

The caller proposes the input configuration, not its correctness as a goal.
Only observed changed pixels count as completed edits. Retries are bounded.
"""
import copy

class EditLoop:
    def __init__(self,points,action=6,verify=True,max_attempts=3):
        self.points=tuple(map(tuple,points));self.action=action;self.verify=verify;self.max_attempts=max_attempts
        self.index=0;self.pending=None;self.attempts={};self.evidence=[];self.original={};self.t=0;self.failed=False
    def propose(self,raw):
        assert set(raw)=={'frame','state','available_actions','levels_completed'}
        if raw['state']!='NOT_FINISHED':return None
        if not self.original:self.original={p:raw['frame'][p[1]][p[0]] for p in self.points}
        if self.pending:
            p=self.pending;point=p['point'];now=raw['frame'][point[1]][point[0]]
            changed=now!=p['before'];self.evidence.append(dict(source=p['source'],point=point,before=p['before'],after=now,changed=changed))
            if changed or not self.verify:self.index+=1
            elif self.attempts[point]>=self.max_attempts:self.failed=True
            self.pending=None
        if self.failed or self.index>=len(self.points):return None
        point=self.points[self.index];self.attempts[point]=self.attempts.get(point,0)+1
        assert self.action in raw['available_actions']
        self.pending=dict(source=self.t,point=point,before=raw['frame'][point[1]][point[0]])
        cert=dict(kind='observed_edit_completion',point=point,attempt=self.attempts[point],previous_evidence=copy.deepcopy(self.evidence),configuration_is_hypothesis=True)
        self.t+=1
        return dict(action=self.action,data=dict(x=point[0],y=point[1]),certificate=cert)
    def completed(self,raw):
        return not self.failed and self.pending is None and self.index==len(self.points) and all(raw['frame'][y][x]!=self.original[x,y] for x,y in self.points)
