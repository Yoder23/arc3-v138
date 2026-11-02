"""Position-conditioned motion hypotheses from prior legal observations only.

The authored modular-coordinate grammar describes nonuniform screen spacing.
It is not a hidden game-state reader or proof of actor identity/causality.
"""
from collections import defaultdict
from temporal_effect_memory import visible
from temporal_effect_memory_v4 import Memory as BaseMemory


class Memory(BaseMemory):
    def models(self, signature, action):
        rows = self.rows[(signature, action)]
        moving = [r for r in rows if r['delta'] != (0, 0)]
        if len({r['delta'] for r in moving}) < 2:
            return []
        models = []
        for axis in (0, 1):
            for period in range(2, 17):
                groups = defaultdict(list)
                for r in moving:
                    groups[r['origin'][axis] % period].append(r)
                if len(groups) < 2:
                    continue
                if any(len({r['delta'] for r in rs}) != 1 for rs in groups.values()):
                    continue
                models.append(dict(axis=axis, period=period, groups=groups))
        return models

    def phase_predictions(self, before, action):
        predictions = []
        for signature, part in self.parts(before).items():
            if signature not in self.moved:
                continue
            origin = tuple(part['origin_rc']); supported = []
            for model in self.models(signature, action):
                q = origin[model['axis']] % model['period']; rows = model['groups'].get(q, [])
                if len(rows) < 3 or len({r['origin'] for r in rows}) < 2:
                    continue
                # Both outcomes must generalize across positions, so a phase
                # partition cannot simply memorize a pair of locations.
                if any(len({r['origin'] for r in rs}) < 2 for rs in model['groups'].values()):
                    continue
                delta = rows[0]['delta']
                if any(r['origin']==origin and r['delta']!=delta for r in self.rows[(signature, action)]):
                    continue
                supported.append((model, rows, delta))
            if not supported or len({d for m,rs,d in supported}) != 1:
                continue
            delta = supported[0][2]
            frame=before['frame']; occupied={tuple(p) for p in part['cells_rc']}
            destination=[(y+delta[0],x+delta[1]) for y,x in occupied]
            if not all(0<=y<len(frame) and 0<=x<len(frame[0]) and ((y,x) in occupied or frame[y][x] in self.vacated_labels[signature]) for y,x in destination):
                continue
            predictions.append(dict(label=signature[0],shape_rc=[list(p) for p in signature[1]],origin_rc=list(origin),delta_rc=list(delta),
                status='position_phase',models=[dict(axis=m['axis'],period=m['period'],support=sorted({r['evidence_hash'] for rs2 in m['groups'].values() for r in rs2})) for m,rs,d in supported],
                observed_vacated_surface_labels=sorted(self.vacated_labels[signature]),
                assumptions=['Unique appearance correspondence','Modular screen coordinate is a provisional context','Unobserved obstacles may refute a forecast']))
        return predictions

    def predict(self, before, action):
        old = super().predict(before, action)
        occupied = {(p['label'],tuple(tuple(q) for q in p['shape_rc'])) for p in old}
        return old+[p for p in self.phase_predictions(before,action) if (p['label'],tuple(tuple(q) for q in p['shape_rc'])) not in occupied]

    def action_contrasts(self, signature):
        by_origin=defaultdict(lambda:defaultdict(set))
        for (sig,action),rows in self.rows.items():
            if sig==signature:
                for r in rows:by_origin[r['origin']][action].add(r['delta'])
        return sum(any(len(left)==len(right)==1 and left!=right for a,left in effects.items() for b,right in effects.items() if a<b) for effects in by_origin.values())
