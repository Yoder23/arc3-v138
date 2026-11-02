"""Transfer a measured position-conditioned model into receding-horizon plans."""
from temporal_planner_v2 import TemporalPlanner as Base
from phase_effect_memory import Memory

class PhasePlanner(Base):
    def __init__(self, *, phase=True, **kwargs):
        super().__init__(**kwargs);self.phase_enabled=phase
        if phase:self.temporal=Memory(True)

    def models(self, signature):
        old=super().models(signature)
        if old or not self.phase_enabled:return old
        if self.temporal.action_contrasts(signature)<2:return []
        actions=sorted({a for sig,a in self.temporal.rows if sig==signature});tables={};locals_={};has_phase=False
        for a in actions:
            rows=self.temporal.rows[(signature,a)];moving=[r for r in rows if r['delta']!=(0,0)]
            for r in rows:locals_.setdefault((a,r['origin']),set()).add(r['delta'])
            values={r['delta'] for r in moving};fits=[]
            if len(values)==1 and len(moving)>=3 and len({r['origin'] for r in moving})>=2:
                fits.append(dict(axis=0,period=1,table={0:next(iter(values))},support={0:sorted({r['evidence_hash'] for r in moving})}))
            elif len(values)>1:
                for m in self.temporal.models(signature,a):
                    if any(len(rs)<3 or len({r['origin'] for r in rs})<2 for rs in m['groups'].values()):continue
                    fits.append(dict(axis=m['axis'],period=m['period'],table={q:rs[0]['delta'] for q,rs in m['groups'].items()},support={q:sorted({r['evidence_hash'] for r in rs}) for q,rs in m['groups'].items()}))
                has_phase |= bool(fits)
            if fits:tables[a]=fits
        if not has_phase or len(tables)<2:return []
        return [dict(kind='position_phase',trigger=-1,state=0,actions=tables,local=locals_)]

    @staticmethod
    def transition(models,modes,origin,action):
        if models[0]['kind']!='position_phase':return Base.transition(models,modes,origin,action)
        m=models[0];fits=m['actions'].get(action,[]);deltas=[];support=[]
        if not fits:return None
        for f in fits:
            q=origin[f['axis']]%f['period'];d=f['table'].get(q)
            if d is None:return None
            deltas.append(d);support.extend(f['support'][q])
        if len(set(deltas))!=1:return None
        d=deltas[0]
        if any(old!=d for old in m['local'].get((action,origin),set())):return None
        return d,(0,),sorted(set(support))
