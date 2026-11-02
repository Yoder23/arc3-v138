"""Measured episode-local endpoints; contradictions suspend global extrapolation."""
from collections import defaultdict
from math import gcd
from copy import deepcopy
from evidence import components, digest
from translation_memory import TransitionMemory as GlobalMemory


class TransitionMemory(GlobalMemory):
    def __init__(self, prior=None):
        super().__init__(prior)
        self.local = defaultdict(list)
        self.suspended = set()
        self.seen = set()

    def periodic_prediction(self, action, origin):
        # This is an authored candidate grammar. The period, axis, anchor and
        # direction must be induced from measured endpoints of this appearance.
        rows=[(p,r) for (p,a),rs in self.local.items() if a==action for r in rs if r['delta_rc']!=[0,0]]
        deltas={tuple(r['delta_rc']) for p,r in rows}
        if len(deltas)!=2:return None
        axes=[i for i in (0,1) if all(d[1-i]==0 and d[i]!=0 for d in deltas)]
        if len(axes)!=1:return None
        axis=axes[0];ds=sorted(d[axis] for d in deltas)
        if not ds[0]<0<ds[1]:return None
        period=ds[1]-ds[0];stride=gcd(abs(ds[0]),ds[1])
        if period//stride<3 or period//stride>64:return None
        if any(sum(r['delta_rc'][axis]==d for p,r in rows)<2 for d in ds):return None
        points={p[axis] for p,r in rows}|{p[axis]+r['delta_rc'][axis] for p,r in rows}
        low,high=min(points),max(points)
        if high-low!=period-stride or len(points)!=period//stride:return None
        if any((x-low)%stride for x in points):return None
        if not(low<=origin[axis]<=high) or (origin[axis]-low)%stride:return None
        step=min(ds,key=abs)
        if any(low+(p[axis]-low+step)%period!=p[axis]+r['delta_rc'][axis] for p,r in rows):return None
        delta=[0,0];delta[axis]=low+(origin[axis]-low+step)%period-origin[axis]
        local_rows=self.local.get((tuple(origin),action),[])
        if any(r['delta_rc']!=delta for r in local_rows):return None
        excluded=[r['evidence_hash'] for (p,a),rs in self.local.items() if a==action for r in rs if r['delta_rc']==[0,0]]
        return dict(action=action,delta_rc=delta,local_evidence=[r['evidence_hash'] for p,r in rows],
            stationary_evidence_excluded_from_motion_fit=excluded,
            status='measured_periodic_endpoint_hypothesis',prior_sha256=None,
            inferred_axis=axis,inferred_period=period,episode_local_anchor=low,
            assumptions=['same observed cyclic coordinate span','unblocked effect; observed local stationary exceptions abstain','same action context','appearance correspondence'])

    def prediction(self, action, origin=None):
        if origin is not None:
            rows = self.local.get((tuple(origin), action), [])
            outcomes = {tuple(r['delta_rc']) for r in rows}
            # Contradictory local evidence cannot fall back to a global prior.
            if len(outcomes) > 1:
                return None
            if len(rows) >= 2 and len(outcomes) == 1:
                return dict(action=action, delta_rc=list(next(iter(outcomes))),
                    local_evidence=[r['evidence_hash'] for r in rows],
                    status='supported_local_endpoint', prior_sha256=None)
        if origin is not None and action in self.suspended:
            periodic=self.periodic_prediction(action,origin)
            if periodic is not None:return periodic
        if action in self.suspended:
            return None
        return super().prediction(action)

    def learn(self, ledger, evidence_hash, actor, *, allow_revision=True, before=None, after=None):
        record = ledger.observation_record(evidence_hash)
        measured = record['measurement']; action = record['action']
        if not measured['comparable'] or measured['boundary']:
            return dict(status='unknown_boundary_or_shape')
        if evidence_hash in self.seen:
            return dict(status='already_recorded')
        matches = [m for m in measured['motions'] if m['label'] == actor['label'] and m['shape_rc'] == actor['shape_rc']]
        origin = delta = None
        if len(matches) == 1:
            origin, delta = matches[0]['before_rc'], matches[0]['delta_rc']
        elif before is not None and after is not None:
            if digest(before) != record['before_sha256'] or digest(after) != record['after_sha256']:
                raise ValueError('Local memory requires the measured public frames')
            parts = [[c for c in components(o['frame']) if c['label'] == actor['label'] and c['shape_rc'] == actor['shape_rc']] for o in (before, after)]
            if len(parts[0]) == len(parts[1]) == 1 and parts[0][0]['cells_rc'] == parts[1][0]['cells_rc']:
                origin, delta = parts[0][0]['origin_rc'], [0, 0]
        if origin is None:
            return dict(status='unknown_correspondence')
        self.seen.add(evidence_hash)
        rows = self.local[(tuple(origin), action)]
        prior_outcomes = {tuple(r['delta_rc']) for r in rows}
        rows.append(dict(delta_rc=list(delta), evidence_hash=evidence_hash))
        previous = self.rules.get(action)
        if prior_outcomes and tuple(delta) not in prior_outcomes:
            self.revisions.append(dict(kind='local_endpoint_conflict', action=action,
                before_rc=list(origin), evidence_hash=evidence_hash,
                previous_outcomes=[list(d) for d in sorted(prior_outcomes)], measured_delta_rc=list(delta),
                applied=True, status='unresolved_no_latest_value_overwrite'))
        if delta == [0, 0]:
            return dict(status='measured_stationary_endpoint', evidence_hash=evidence_hash)
        if previous is not None and previous['delta_rc'] != delta:
            imported = not previous['local_evidence'] and previous['prior_sha256'] is not None
            if imported and action not in self.suspended:
                # Preserve v2's evidence-based demotion of imported control context.
                return super().learn(ledger, evidence_hash, actor, allow_revision=allow_revision)
            if action not in self.suspended:
                self.revisions.append(dict(kind='global_translation_suspended', action=action,
                    previous_rule=deepcopy(previous), measured_delta_rc=list(delta),
                    evidence_hash=evidence_hash, applied=bool(allow_revision)))
                if allow_revision:
                    self.suspended.add(action)
            return dict(status='conditional_effect_global_unknown', evidence_hash=evidence_hash)
        if action in self.suspended:
            return dict(status='global_suspended_local_evidence_retained', evidence_hash=evidence_hash)
        return super().learn(ledger, evidence_hash, actor, allow_revision=allow_revision)

    def export(self):
        result = super().export()
        result['rules'] = [r for r in result['rules'] if r['action'] not in self.suspended]
        return result

    def local_report(self):
        return [dict(before_rc=list(p), action=a, observations=deepcopy(rows),
            ambiguous=len({tuple(r['delta_rc']) for r in rows}) > 1)
            for (p, a), rows in sorted(self.local.items())]
