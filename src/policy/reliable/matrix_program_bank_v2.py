"""Bind visible reference masks to a blank input; retain their pixel sources."""
import copy
from matrix_local_body_crop_v2 import Agent as Base
from matrix_reference_programs_v1 import programs
from matrix_reference_cues_v2 import cues
from matrix_motion_learner_v6 import objects
from matrix_intermediate_learner_v3 import gap
from observed_program_completion_v1 import ProgramEditLoop
class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.program_bindings=[];self.program_bank_bound_at=None;self.disable_program_bank=False;self.program_editors=[]
    def reference_targets(self,raw):
        if not self.grid or not self.moving or self.effect_seen_level==raw['levels_completed']:return []
        ps=programs(raw['frame'],self.grid);excluded=[self.grid['box']]+[p['panel'] for p in ps];ink={c['ink'] for c in cues(raw,self.grid)}
        return [o for o in objects(raw['frame'],excluded) if not o.get('parts') and o['ink'] in ink and gap(o['box'],self.grid['box'])>12]
    def issue(self,raw,action,data,phase,route=None,extra=None):
        if phase!='motion_inquiry' and self.reference_targets(raw) and len(self.orientations)>=2:
            if not hasattr(self,'executed_intermediate_keys'):self.executed_intermediate_keys=set()
            key=(tuple(self.experiment['landmark']['box']),self.experiment['landmark']['ink']) if self.experiment else None
            if key and key not in self.executed_intermediate_keys:self.attempted.discard(key)
            self.experiment=None
            return dict(done=True,action=None,data={})
        return super().issue(raw,action,data,phase,route,extra)
    def answer(self,raw,action,data,tag,extra=None):
        extra=dict(extra or {})
        if tag=='verify_input_edit' and self.grid and self.program_bank_bound_at!=self.grid['observed_at']:
            self.program_bank_bound_at=self.grid['observed_at'];self.program_bindings=[]
            ps=programs(raw['frame'],self.grid);values={raw['frame'][y][x] for y,x,h,w in self.grid['cells']}
            if not self.disable_program_bank and len(values)==1 and ps:
                obs=objects(raw['frame'],[self.grid['box']]+[p['panel'] for p in ps]);inks={o['ink'] for o in obs if not o.get('parts')}
                ps=sorted(ps,key=lambda p:(p['ink'] not in inks,len(p['indices']),p['panel']))
                self.programs=[]
                for p in ps:
                    points=[(self.grid['cells'][i][1]+(self.grid['cells'][i][3]-1)//2,self.grid['cells'][i][0]+(self.grid['cells'][i][2]-1)//2) for i in p['indices']]
                    self.programs.append(points);self.program_bindings.append(dict(source=self.t,reference=copy.deepcopy(p),grid=copy.deepcopy(self.grid),points=points,hypothesis='copy_visible_reference_mask_to_input_cells'))
                self.program_index=0;self.edit=ProgramEditLoop(self.programs[0],self.grid,self.t);self.program_editors.append(self.edit);self.edit_started_at=self.t;proposal=self.edit.propose(raw);action=proposal['action'];data=proposal['data'];extra.update(edit=proposal['certificate'],edit_start=self.t)
        extra['program_bindings']=copy.deepcopy(self.program_bindings)
        extra['program_execution_acks']=[copy.deepcopy(e.acknowledgement) for e in self.program_editors if e.acknowledgement]
        return super().answer(raw,action,data,tag,extra)
