"""Remember failed transition contexts and test a reversible detour before repeating them."""
import copy
from selectable_temporal_recovery_v4 import Agent as Base
class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.transition_contexts=[];self.context_probe=None;self.context_probe_history=[];self.context_probe_attempts=0;self.probed_context_sources=set()
    def reset_level(self,raw):
        super().reset_level(raw);self.context_probe=None;self.context_probe_attempts=0
    def values(self,raw,box):
        y,x,h,w=box;return [raw['frame'][a][b] for a in range(y,y+h) for b in range(x,x+w)]
    def observe(self,raw):
        old=self.previous;n=len(self.control_exceptions);r=super().observe(raw)
        for p in self.control_exceptions[n:]:
            before=p['actual']['before'];dy,dx=p['expected']['delta'];y,x,h,w=before['box'];margin=max(abs(dy),abs(dx));yy=max(0,y+dy-margin);xx=max(0,x+dx-margin);box=(yy,xx,min(64,y+dy+h+margin)-yy,min(64,x+dx+w+margin)-xx)
            self.transition_contexts.append(dict(source=p['source'],level=raw['levels_completed'],action=p['actual']['action'],origin=copy.deepcopy(before),delta=p['expected']['delta'],window=box,values=self.values(old['raw'],box),cause_unconfirmed=True))
        return r
    def respond(self,raw):
        if raw['state']=='NOT_FINISHED' and self.level==raw['levels_completed']:
            bodies=self.detect_objects(raw)
            if len(bodies)==1:
                body=bodies[0];state=self.context_probe
                if state:
                    if state['phase']=='return' and tuple(body['box'])==tuple(state['away']):
                        self.observe(raw);a=state['reverse'];state['phase']='finish';state['end']=self.t
                        r=self.answer(raw,a,{},'return_after_context_detour',self.objects[0],[a]);r['certificate']['context_probe']=copy.deepcopy(state);return r
                    self.context_probe=None
                    if state['phase']=='finish' and tuple(body['box'])==tuple(state['origin']['box']):
                        self.probed_context_sources.add(state['failure_source']);self.context_probe_history.append(dict(start=state['start'],end=state['end'],failure_source=state['failure_source'],origin=state['origin'],window=state['window'],before=state['before'],after=self.values(raw,state['window']),returned=True))
                matches=[p for p in self.transition_contexts if p['source'] not in self.probed_context_sources and p['level']==self.level and tuple(p['origin']['box'])==tuple(body['box']) and self.values(raw,p['window'])==p['values']]
                if matches:
                    if self.context_probe_attempts>=8:return dict(done=True,action=None,data={},context_probe_history=copy.deepcopy(self.context_probe_history))
                    p=matches[-1];allowed={self.floor}|set(self.passive_terrain_memory)|{g['ink'] for g in self.goals};y,x,h,w=body['box'];choices=[]
                    for a,m in sorted(self.motions.items()):
                        if a==p['action']:continue
                        dy,dx=m['delta'];q=(y+dy,x+dx,h,w);reverse=next((b for b,n in sorted(self.motions.items()) if tuple(n['delta'])==(-dy,-dx)),None)
                        if reverse is None or not(0<=q[0]<=64-h and 0<=q[1]<=64-w):continue
                        if any(not(y<=yy<y+h and x<=xx<x+w) and raw['frame'][yy][xx] not in allowed for yy in range(q[0],q[0]+h) for xx in range(q[1],q[1]+w)):continue
                        choices.append((a,reverse,q))
                    if choices:
                        a,reverse,away=choices[0];self.passive_probe_state=None;self.observe(raw);body=self.objects[0];self.context_probe_attempts+=1
                        state=dict(phase='return',start=self.t,reverse=reverse,away=away,origin=copy.deepcopy(body),failure_source=p['source'],window=p['window'],before=p['values'],hypothesis='reversible_motion_may_change_the_failed_transition_context');self.context_probe=state
                        r=self.answer(raw,a,{},'test_changed_context_detour',body,[a,reverse]);r['certificate']['context_probe']=copy.deepcopy(state);return r
        return super().respond(raw)
    def answer(self,*args,**kwargs):
        r=super().answer(*args,**kwargs)
        if not r['done']:
            if self.transition_contexts:r['certificate']['transition_contexts']=copy.deepcopy(self.transition_contexts)
            if self.context_probe_history:r['certificate']['context_probe_history']=copy.deepcopy(self.context_probe_history)
        return r
