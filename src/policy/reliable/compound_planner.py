"""Prefer a supported connected appearance over contained animated fragments.

This is a perception/model-selection prior, not proof of physical attachment.
Every nominee must already pass its own action-effect evidence requirements.
"""
from phase_planner import PhasePlanner
from temporal_effect_memory import visible

class CompoundPlanner(PhasePlanner):
    def __init__(self, *, compound=True, global_model=True, **kwargs):
        super().__init__(**kwargs);self.compound_enabled=compound;self.global_model_enabled=global_model
        if not compound:
            from temporal_effect_memory import primitive_visible
            self.temporal.parts=primitive_visible

    def models(self, signature):
        supported=super().models(signature)
        if supported or not self.global_model_enabled or self.temporal.action_contrasts(signature)<2:return supported
        tables={};locals_={}
        for (sig,action),rows in self.temporal.rows.items():
            if sig!=signature:continue
            moving=[r for r in rows if r['delta']!=(0,0)]
            values={r['delta'] for r in moving}
            for r in rows:locals_.setdefault((action,r['origin']),set()).add(r['delta'])
            if len(values)==1 and len(moving)>=3 and len({r['origin'] for r in moving})>=2:
                tables[action]=[dict(axis=0,period=1,table={0:next(iter(values))},support={0:sorted({r['evidence_hash'] for r in moving})})]
        if len(tables)<2 or len({v[0]['table'][0] for v in tables.values()})<2:return []
        return [dict(kind='global_action',trigger=-1,state=0,actions=tables,local=locals_)]

    @staticmethod
    def transition(models,modes,origin,action):
        if models[0]['kind']!='global_action':return PhasePlanner.transition(models,modes,origin,action)
        m=models[0];f=m['actions'].get(action)
        if not f:return None
        delta=f[0]['table'][0]
        if any(old!=delta for old in m['local'].get((action,origin),set())):return None
        return delta,(0,),f[0]['support'][0]

    def select_nominees(self, nominees, obs):
        if not self.compound_enabled:return nominees
        remove=set();revisions=[]
        def history(sig):
            return {r['evidence_hash']:dict(r,action=a) for (key,a),rows in self.temporal.rows.items() if key==sig for r in rows}
        histories={sig:history(sig) for sig,part,models in nominees}
        for i,(small,part,models) in enumerate(nominees):
            small_cells={tuple(p) for p in part['cells_rc']}
            for j,(large,whole,other_models) in enumerate(nominees):
                if i==j or large[0]<16 or not small_cells<{tuple(p) for p in whole['cells_rc']}:continue
                a,b=histories[small],histories[large];common=set(a)&set(b)
                if len(common)<4 or len({b[h]['action'] for h in common if b[h]['delta']!=(0,0)})<2:continue
                contained=True
                for h in common:
                    for after in (False,True):
                        ay,ax=a[h]['origin'];by,bx=b[h]['origin']
                        if after:ay+=a[h]['delta'][0];ax+=a[h]['delta'][1];by+=b[h]['delta'][0];bx+=b[h]['delta'][1]
                        left={(ay+y,ax+x) for y,x in small[1]};right={(by+y,bx+x) for y,x in large[1]}
                        if not left<right:contained=False;break
                    if not contained:break
                if contained:
                    remove.add(i);revisions.append(dict(fragment_label=small[0],fragment_shape_rc=[list(p) for p in small[1]],whole_label=large[0],whole_shape_rc=[list(p) for p in large[1]],support=sorted(common)))
                    break
        self.current_grouping=revisions
        return [v for i,v in enumerate(nominees) if i not in remove]

    def choose(self,obs):
        self.current_grouping=[];result=super().choose(obs)
        if self.current_grouping:self.decisions[-1]['appearance_grouping']=self.current_grouping
        return result

    def run(self,initial,step,*,max_actions=256):
        result=super().run(initial,step,max_actions=max_actions)
        result['temporal_model_grammar']='connected_appearance_with_global_temporal_or_position_phase_effects'
        return result
