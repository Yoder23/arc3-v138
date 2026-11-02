"""Compare action and successful-movement clocks against visible and occluded controls."""
from collections import defaultdict
from key_control_clock_v2 import at,refresh,intercept

def learn(history,models,controls,t,clock_ticks,actor):
    by=defaultdict(list)
    for c in controls:by[c['signature']].append(c)
    for sig,items in by.items():
        if len(items)==1:history.setdefault(sig,{})[t]=items[0]['box']
    for sig,h in history.items():
        recent={k:v for k,v in h.items()if k>=t-64}
        if len(set(recent.values()))<2:continue
        prior=models.get(sig,{});candidates={};refutations=list(prior.get('visibility_refutations',[]))
        for basis in ['action','movement']:
            for period in range(2,17):
                phases=defaultdict(list)
                for source,box in recent.items():
                    index=source if basis=='action'else clock_ticks[source]
                    phases[index%period].append(box)
                if len(phases)!=period or not all(len(v)>=2 and len(set(v))==1 for v in phases.values()):continue
                raw=tuple(phases[k][0]for k in range(period));tick=t if basis=='action'else clock_ticks[t];predicted=raw[tick%period]
                y,x,h,w=predicted;inside=actor[0]<=y+h//2<actor[0]+actor[2]and actor[1]<=x+w//2<actor[1]+actor[3]
                if not by.get(sig)and not inside:
                    evidence=dict(source=t,basis=basis,predicted_box=predicted,hypothesis='predicted_control_should_be_visible_outside_actor')
                    if evidence not in refutations:refutations.append(evidence)
                    continue
                offset=0 if basis=='action'else clock_ticks[t]-t
                candidates[basis]=dict(period=period,basis=basis,raw_positions=raw,positions=tuple(raw[(k+offset)%period]for k in range(period)),sources=tuple(sorted(recent)),visibility_refutations=refutations)
                break
        order=['movement','action']if prior.get('basis')=='movement'else['action','movement']
        chosen=next((candidates[b]for b in order if b in candidates),None)
        if chosen:models[sig]=chosen
        else:models.pop(sig,None)

def observed_at(control,models,source,clock_ticks):
    model=models.get(control['signature'])
    if model and model.get('basis')=='movement'and source in clock_ticks:
        return dict(control,box=model['raw_positions'][clock_ticks[source]%model['period']])
    return at(control,models,source)
