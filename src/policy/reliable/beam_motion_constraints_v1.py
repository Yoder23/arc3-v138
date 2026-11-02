"""Repeated unobstructed no-motion observations propose a local movement bound."""
from collections import defaultdict
def infer(failures):
    groups=defaultdict(list)
    for f in failures:
        if f['kind']!='bar_motion_blocked':continue
        axis=0 if f['action']in (1,2)else 1
        groups[(f['index'],f['action'],f['position'][axis])].append(f)
    result={}
    for (index,action,value),rows in groups.items():
        axis=0 if action in (1,2)else 1
        if len({r['position'][1-axis]for r in rows})<2:continue
        key={1:'min_y',2:'max_y',3:'min_x',4:'max_x'}[action]
        result.setdefault(index,{})[key]=dict(value=value,sources=sorted(r['source']for r in rows))
    return result
def allowed(index,position,limits):
    tests={'min_y':position[0], 'max_y':position[0], 'min_x':position[1], 'max_x':position[1]}
    return all(tests[k]>=v['value']if k.startswith('min')else tests[k]<=v['value']for k,v in limits.get(index,{}).items())
