from learner import *
from evidence import digest
from adaptive_acquisition import AdaptivePlanner as Base
from phase_effect_memory import Memory
from temporal_effect_memory import visible

class PhaseStream(Base):
    def ingest(self,current,action,after):
        decision=self.decisions[-1]
        if current['levels_completed']!=after['levels_completed'] or after['state']!='NOT_FINISHED':
            self.contact_blocked.clear();vision=self.temporal.parts;self.temporal=Memory(True);self.temporal.parts=vision;self.temporal_rejections.clear()
            return
        if decision['temporal']:
            key=(decision['actor']['label'],tuple(tuple(p) for p in decision['actor']['shape_rc']))
            left,right=self.temporal.parts(current).get(key),self.temporal.parts(after).get(key)
            if left and right:
                dy=right['origin_rc'][0]-left['origin_rc'][0];dx=right['origin_rc'][1]-left['origin_rc'][1]
                if (dy,dx)==(0,0) and decision['prediction']['delta_rc']!=[0,0]:
                    y,x=left['origin_rc'];py,px=decision['prediction']['delta_rc'];shape=left['shape_rc'];f=current['frame']
                    labels={f[y+py+r][x+px+c] for r,c in shape if 0<=y+py+r<len(f) and 0<=x+px+c<len(f[0])}
                    if labels=={decision['target']['label']}:
                        self.contact_blocked.update(labels);self.contact_revisions.append(dict(step=self.action_count,kind='contact_material_provisionally_rejected',labels=sorted(labels),evidence_hash=digest(dict(before=current,action=action,after=after))))
                elif (dy,dx)!=(0,0):
                    old={tuple(p) for p in left['cells_rc']};entered={current['frame'][r][c] for r,c in right['cells_rc'] if (r,c) not in old}
                    for label in entered & self.contact_blocked:
                        self.contact_blocked.remove(label);self.contact_revisions.append(dict(step=self.action_count,kind='contact_rejection_refuted',label=label))
        self.temporal.observe(current,action,after)

    def interact(self, initial, *, max_actions=128):
        if type(max_actions) is not int or max_actions < 1:
            raise ValueError('Positive action budget required')
        current = observation(initial)
        while current['state'] == 'NOT_FINISHED' and self.action_count < max_actions:
            (action, prediction, purpose) = self.choose(current)
            actor_before = self.locate_actor(current)
            rule_before = self.memory.prediction(action, actor_before['origin_rc'] if actor_before else None)
            position = tuple(actor_before['origin_rc']) if actor_before else None
            self.attempts[position, action] += 1
            self.ledger.predict(current, action, prediction)
            self.action_count += 1
            after = observation((yield dict(action=action, prediction=prediction, purpose=purpose)))
            self.ingest(current, action, after)
            result = self.ledger.observe(after)
            if result['measurement']['boundary'] or not result['measurement']['comparable']:
                self.reset_scene('scene_boundary_or_noncomparable', result['evidence_hash'])
                self.events.append(dict(step=self.action_count, purpose=purpose, action=action, prediction_status=result['prediction_status'], learned=dict(status='no_cross_boundary_learning'), evidence_hash=result['evidence_hash']))
                current = after
                continue
            self.control_hypotheses.update(self.ledger, result['evidence_hash'], current, after)
            nominees = self.control_hypotheses.nominate(after)
            self.control_authority = bool(len(nominees) == 1 and (self.actor is None or nominees[0]['actor'] == self.actor))
            if self.actor is not None and self.locate_actor(after) is None:
                self.reset_scene('actor_localization_unknown', result['evidence_hash'])
                nominees = []
                actor_before = None
                position = None
                rule_before = None
            if self.actor is not None and (not nominees):
                if not self.actor_events or self.actor_events[-1]['status'] != 'appearance_retained_control_model_uncertain':
                    self.actor_events.append(dict(step=self.action_count, actor=deepcopy(self.actor), status='appearance_retained_control_model_uncertain', evidence_hash=result['evidence_hash']))
            if self.actor is not None and nominees and (len(nominees) != 1 or nominees[0]['actor'] != self.actor):
                self.actor_events.append(dict(step=self.action_count, actor=deepcopy(self.actor), status='revoked_stationary_control_hypothesis', evidence_hash=result['evidence_hash']))
                self.knowledge_epochs.append(dict(reason='ambiguous_actor_authority', ended_by=result['evidence_hash'], knowledge=self.memory.export(), revisions=deepcopy(self.memory.revisions), local_endpoints=self.memory.local_report(), suspended_global_actions=sorted(self.memory.suspended), active_local_claim=False))
                self.revision_history.extend(deepcopy(self.memory.revisions))
                self.actor = None
                self.control_authority = False
                self.memory = TransitionMemory()
                self.floor_labels.clear()
                self.blocked.clear()
                self.blocking_labels.clear()
                self.visits.clear()
                self.attempts.clear()
                self.target_rejections.clear()
                actor_before = None
                position = None
                rule_before = None
            if self.actor is None and len(nominees) == 1:
                nominee = nominees[0]
                self.actor = nominee['actor']
                self.control_authority = True
                self.actor_events.append(dict(step=self.action_count, actor=deepcopy(self.actor), status=nominee['status'], support=[r['evidence_hash'] for r in nominee['support']]))
                for support in nominee['support']:
                    self.floor_labels.update(support['vacated_labels'])
                    self.memory.learn(self.ledger, support['evidence_hash'], self.actor, allow_revision=self.revise)
                actor_before = self.locate_actor(current)
            if self.actor is not None:
                if self.control_authority:
                    self.learn_collision(current, after, actor_before, result, rule_before)
                if actor_before:
                    actor_after = self.locate_actor(after)
                    occupied = {tuple(p) for p in actor_after['cells_rc']} if actor_after else {tuple(p) for p in actor_before['cells_rc']}
                    for (y, x) in actor_before['cells_rc']:
                        if (y, x) not in occupied:
                            self.floor_labels.add(after['frame'][y][x])
                revisions_before = len(self.memory.revisions)
                learned = self.memory.learn(self.ledger, result['evidence_hash'], self.actor, allow_revision=self.revise, before=current, after=after)
                if len(self.memory.revisions) > revisions_before:
                    self.blocked.clear()
                    self.blocking_labels.clear()
                    self.target_rejections.clear()
                if self.control_authority and position is not None and (result['observed_delta_rc'] == [0, 0]):
                    self.blocked.add((position, action))
                elif position is not None and result['observed_delta_rc'] is not None:
                    self.blocked.discard((position, action))
            else:
                learned = dict(status='actor_not_identified')
            self.events.append(dict(step=self.action_count, purpose=purpose, action=action, prediction_status=result['prediction_status'], learned=learned, evidence_hash=result['evidence_hash']))
            current = after
        assert self.ledger.verify()
        out = dict(won=current['state'] == 'WIN', actions=self.action_count, final_state=current['state'], stop_reason='terminal' if current['state'] != 'NOT_FINISHED' else 'action_budget', learned_knowledge=self.memory.export(), revisions=deepcopy(self.revision_history + self.memory.revisions), refuted_predictions=sum((e['prediction_status'] == 'refuted' for e in self.events)), events=deepcopy(self.events), evidence=self.ledger.rows, actual_model_calls=0, actor_hypotheses=deepcopy(self.actor_events), collision_hypotheses=deepcopy(self.collision_events), historical_knowledge_epochs=deepcopy(self.knowledge_epochs), local_endpoint_table=self.memory.local_report(), current_control_authority=self.control_authority, public_score=False, scope='authored_translation_worlds_only')
        out['temporal_decisions'] = deepcopy(self.decisions)
        out['temporal_actions'] = sum((d['temporal'] for d in self.decisions))
        out['temporal_model_grammar'] = 'evidence_ready_acquisition_with_connected_action_models'
        out['contact_revisions'] = self.contact_revisions[:]
        return out

