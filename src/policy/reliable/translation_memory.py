"""Provisional action-effect memory. Exported rules remain hypotheses in new worlds."""
from copy import deepcopy
from evidence import digest


class TransitionMemory:
    def __init__(self, prior=None):
        self.rules, self.revisions, self.ambiguous = {}, [], []
        if prior is not None:
            if prior.get('schema') != 'translation-prior-v1':
                raise ValueError('Unknown knowledge schema')
            for row in prior['rules']:
                action, delta = row['action'], row['delta_rc']
                if type(action) is not int or type(delta) is not list or len(delta) != 2 or any(type(x) is not int for x in delta) or delta == [0,0]:
                    raise ValueError('Invalid prior rule')
                if action in self.rules:
                    raise ValueError('Duplicate prior action')
                self.rules[action] = dict(action=action, delta_rc=list(delta), local_evidence=[],
                                          status='retrieved_unverified', prior_sha256=digest(row))

    def prediction(self, action):
        row = self.rules.get(action)
        return deepcopy(row) if row else None

    def learn(self, ledger, evidence_hash, actor, *, allow_revision=True):
        """Use an executed, measured transition, not the model's prose interpretation."""
        result = ledger.observation_record(evidence_hash)
        action, measured = result['action'], result['measurement']
        if not measured['comparable'] or measured['boundary']:
            return dict(status='unknown_boundary_or_shape')
        matches = [m for m in measured['motions'] if m['label'] == actor['label'] and m['shape_rc'] == actor['shape_rc']]
        if len(matches) != 1:
            self.ambiguous.append(dict(action=action,evidence_hash=result['evidence_hash'],reason='no_unique_nonzero_motion'))
            return dict(status='unknown_or_blocked')
        delta = matches[0]['delta_rc']; previous = self.rules.get(action)
        if previous and previous['delta_rc'] != delta:
            # A contradicted imported context makes its other untested rules suspect.
            # This is a heuristic hypothesis reset, not evidence they are all wrong.
            trigger_imported = not previous['local_evidence'] and previous['prior_sha256'] is not None
            cleared = [a for a,r in self.rules.items() if a!=action and not r['local_evidence']
                       and r['prior_sha256'] is not None] if trigger_imported and allow_revision else []
            revision = dict(action=action, rejected_delta_rc=previous['delta_rc'], measured_delta_rc=delta,
                            evidence_hash=result['evidence_hash'], previous_rule=deepcopy(previous),
                            applied=bool(allow_revision),cleared_unverified_actions=sorted(cleared),
                            retained_measured_actions=sorted(a for a,r in self.rules.items() if r['local_evidence']),
                            context_change_hypothesis=bool(trigger_imported and allow_revision))
            self.revisions.append(revision)
            if not allow_revision:
                return dict(status='revision_withheld_by_ablation', retained_delta_rc=list(previous['delta_rc']),
                            measured_delta_rc=list(delta), evidence_hash=result['evidence_hash'])
            for untested_action in cleared:
                del self.rules[untested_action]
            previous = None
        if previous is None:
            previous = dict(action=action,delta_rc=list(delta),local_evidence=[],status='observed_once',prior_sha256=None)
            self.rules[action] = previous
        if result['evidence_hash'] not in previous['local_evidence']:
            previous['local_evidence'].append(result['evidence_hash'])
        previous['status'] = 'locally_supported' if len(previous['local_evidence']) >= 2 else 'observed_once'
        return deepcopy(previous)

    def export(self):
        # No grids, coordinates, palette labels, goals, task identities or trajectories.
        rows = [dict(action=a,delta_rc=r['delta_rc'],evidence_hashes=list(r['local_evidence']),
                     assumptions=['same action semantics','single stable translated appearance','unblocked movement'])
                for a,r in sorted(self.rules.items()) if r['local_evidence']]
        return dict(schema='translation-prior-v1',learned_from='measured_public_interactions',
                    rules=deepcopy(rows),scope='provisional_control_mapping_not_a_general_game_solver')
