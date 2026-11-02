"""Tentative control attribution from varied interventions, not first motion."""
from copy import deepcopy
from evidence import components,digest
from composite_components import subsume_parts

class ControlHypotheses:
    def __init__(self):
        self.records={};self.previous_action=None

    def update(self,ledger,evidence_hash,before,after):
        result=ledger.observation_record(evidence_hash);m=result['measurement'];action=result['action']
        if digest(before)!=result['before_sha256'] or digest(after)!=result['after_sha256']:
            raise ValueError('Control evidence frames differ from the measured transition')
        if m['comparable'] and not m['boundary']:
            motions=deepcopy(m['motions'])
            visible_before=components(before['frame']);visible_after=components(after['frame'])
            for part in visible_before:
                left=[c for c in visible_before if c['label']==part['label'] and c['shape_rc']==part['shape_rc']]
                right=[c for c in visible_after if c['label']==part['label'] and c['shape_rc']==part['shape_rc']]
                if len(left)==len(right)==1 and part['cells_rc']==right[0]['cells_rc']:
                    motions.append(dict(label=part['label'],shape_rc=part['shape_rc'],before_rc=part['origin_rc'],after_rc=part['origin_rc'],delta_rc=[0,0]))
            for motion in motions:
                key=(motion['label'],tuple(tuple(p) for p in motion['shape_rc']))
                candidates=[c for c in components(before['frame']) if c['label']==key[0] and tuple(tuple(p) for p in c['shape_rc'])==key[1]]
                if len(candidates)!=1:continue
                ay,ax=motion['after_rc'];occupied={(ay+dy,ax+dx) for dy,dx in motion['shape_rc']}
                vacated=[after['frame'][y][x] for y,x in candidates[0]['cells_rc'] if (y,x) not in occupied]
                self.records.setdefault(key,[]).append(dict(action=action,delta=tuple(motion['delta_rc']),
                    before_rc=motion['before_rc'],after_rc=motion['after_rc'],
                    previous_action=self.previous_action,evidence_hash=evidence_hash,vacated_labels=vacated))
        self.previous_action=action

    def nominate(self,current=None):
        candidates=[]
        for key,records in self.records.items():
            by_action={}
            for r in records:by_action.setdefault(r['action'],[]).append(r)
            matched={}
            for row in records:
                matched.setdefault(tuple(row['before_rc']),{}).setdefault(row['action'],[]).append(row)
            contrasts=[]
            for origin, actions in matched.items():
                supported=[rows for rows in actions.values() if len(rows)>=2
                    and len({r['previous_action'] for r in rows})>=2
                    and len({r['delta'] for r in rows})==1]
                if len(supported)>=2 and len({rows[0]['delta'] for rows in supported})>=2:
                    contrasts.append(origin)
            variable=any(len({r['delta'] for r in rows if r['delta']!=(0,0)})>1 for rows in by_action.values())
            if len(contrasts)<(2 if variable else 1):continue
            candidates.append(dict(actor=dict(label=key[0],shape_rc=[list(p) for p in key[1]]),
                support=deepcopy(records),status='matched_position_action_contrasts_not_causal_proof'))
        if current is None:return candidates
        visible=components(current['frame'])
        candidates=[c for c in candidates if sum(o['label']==c['actor']['label'] and o['shape_rc']==c['actor']['shape_rc'] for o in visible)==1]
        return subsume_parts(candidates,current['frame'],visible)
