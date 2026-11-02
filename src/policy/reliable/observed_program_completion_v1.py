"""A program may acknowledge execution by clearing edits or changing a visible object."""
import copy
from observed_edit_completion_v1 import EditLoop
from matrix_motion_learner_v6 import objects
class ProgramEditLoop(EditLoop):
    def __init__(self,points,grid,start):
        super().__init__(points);self.grid=copy.deepcopy(grid);self.start=start;self.before_final=None;self.acknowledgement=None
    def propose(self,raw):
        if self.pending and self.pending['point']==self.points[-1] and self.before_final:
            old=self.before_final;p=self.pending;x,y=p['point'];reset=[(xx,yy,old['frame'][yy][xx],raw['frame'][yy][xx]) for xx,yy in self.points[:-1] if old['frame'][yy][xx]!=raw['frame'][yy][xx] and raw['frame'][yy][xx]==self.original[xx,yy]]
            evidence=None
            if reset and all(raw['frame'][yy][xx]==self.original[xx,yy] for xx,yy in self.points):evidence=dict(kind='observed_collective_input_reset',changed=reset)
            if evidence is None and len(self.points)==1:
                before=objects(old['frame'],[self.grid['box']]);after=objects(raw['frame'],[self.grid['box']])
                for b in before:
                    yy,xx,hh,ww=b['box']
                    if yy==0 or xx==0 or yy+hh==64 or xx+ww==64 or min(hh,ww)<2:continue
                    if b.get('parts'):
                        candidates=[q for q in after if q.get('parts') and q['ink']==b['ink'] and q['box']!=b['box']]
                        if len(candidates)==1:evidence=dict(kind='observed_body_change',before=b,after=candidates[0]);break
                    elif all(raw['frame'][yy+dy][xx+dx]!=b['ink'] for dy,dx in b['shape']):
                        changed=[(yy+dy,xx+dx,b['ink'],raw['frame'][yy+dy][xx+dx]) for dy,dx in b['shape']]
                        if len(changed)>=2:evidence=dict(kind='observed_object_change',before=b,changed=changed);break
            if evidence:
                self.evidence.append(dict(source=p['source'],point=p['point'],before=p['before'],after=raw['frame'][y][x],changed=p['before']!=raw['frame'][y][x]))
                self.acknowledgement=dict(source=self.start+p['source'],start=self.start,point=p['point'],points=self.points,evidence=evidence,goal_confirmed=False)
                self.pending=None;self.index=len(self.points);self.failed=False;return None
        result=super().propose(raw)
        if result and self.pending['point']==self.points[-1]:self.before_final=copy.deepcopy(raw)
        return result
    def completed(self,raw):return self.acknowledgement is not None or super().completed(raw)
