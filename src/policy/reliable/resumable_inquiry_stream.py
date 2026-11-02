"""Serializable phase continuation for failure-driven inquiry and retained memory."""
from contact_inquiry import InquiryStream as Original
from resumable_legacy_learner import Interaction as BaseInteraction
from evidence import observation
from knowledge import TransitionMemory
from copy import deepcopy

class InquiryStream(Original):
    def interact(self,initial,*,max_actions=128):
        return Interaction(self,initial,max_actions)

class Interaction(BaseInteraction):
    def _result(self):
        learner=self.learner;current=self.current
        assert learner.ledger.verify()
        out = dict(won=current['state'] == 'WIN', actions=learner.action_count, final_state=current['state'], stop_reason='terminal' if current['state'] != 'NOT_FINISHED' else 'action_budget', learned_knowledge=learner.memory.export(), revisions=deepcopy(learner.revision_history + learner.memory.revisions), refuted_predictions=sum((e['prediction_status'] == 'refuted' for e in learner.events)), events=deepcopy(learner.events), evidence=learner.ledger.rows, actual_model_calls=0, actor_hypotheses=deepcopy(learner.actor_events), collision_hypotheses=deepcopy(learner.collision_events), historical_knowledge_epochs=deepcopy(learner.knowledge_epochs), local_endpoint_table=learner.memory.local_report(), current_control_authority=learner.control_authority, public_score=False, scope='authored_translation_worlds_only')
        out['temporal_decisions'] = deepcopy(learner.decisions)
        out['temporal_actions'] = sum((d['temporal'] for d in learner.decisions))
        out['temporal_model_grammar'] = 'evidence_ready_acquisition_with_connected_action_models'
        out['contact_revisions'] = learner.contact_revisions[:]
        return out


    def _offer(self):
        if self.closed:raise StopIteration
        learner=self.learner;current=self.current;max_actions=self.max_actions
        if current['state']!='NOT_FINISHED' or learner.action_count>=max_actions:return self._finish()
        (action, prediction, purpose) = learner.choose(current)
        actor_before = learner.locate_actor(current)
        rule_before = learner.memory.prediction(action, actor_before['origin_rc'] if actor_before else None)
        position = tuple(actor_before['origin_rc']) if actor_before else None
        learner.attempts[position, action] += 1
        learner.ledger.predict(current, action, prediction)
        learner.action_count += 1

        self.pending=(action,prediction,purpose,actor_before,rule_before,position)
        return dict(action=action,prediction=prediction,purpose=purpose)
    def send(self,value):
        if self.closed:raise StopIteration
        if not self.started:
            if value is not None:raise TypeError('Cannot send non-None to a new continuation')
            return next(self)
        learner=self.learner;current=self.current
        action,prediction,purpose,actor_before,rule_before,position=self.pending
        after=observation(value)
        learner.ingest(current, action, after)
        result = learner.ledger.observe(after)
        if result['measurement']['boundary'] or not result['measurement']['comparable']:
            learner.reset_scene('scene_boundary_or_noncomparable', result['evidence_hash'])
            learner.events.append(dict(step=learner.action_count, purpose=purpose, action=action, prediction_status=result['prediction_status'], learned=dict(status='no_cross_boundary_learning'), evidence_hash=result['evidence_hash']))
            self.current = after
            return self._offer()
        learner.control_hypotheses.update(learner.ledger, result['evidence_hash'], current, after)
        nominees = learner.control_hypotheses.nominate(after)
        learner.control_authority = bool(len(nominees) == 1 and (learner.actor is None or nominees[0]['actor'] == learner.actor))
        if learner.actor is not None and learner.locate_actor(after) is None:
            learner.reset_scene('actor_localization_unknown', result['evidence_hash'])
            nominees = []
            actor_before = None
            position = None
            rule_before = None
        if learner.actor is not None and (not nominees):
            if not learner.actor_events or learner.actor_events[-1]['status'] != 'appearance_retained_control_model_uncertain':
                learner.actor_events.append(dict(step=learner.action_count, actor=deepcopy(learner.actor), status='appearance_retained_control_model_uncertain', evidence_hash=result['evidence_hash']))
        if learner.actor is not None and nominees and (len(nominees) != 1 or nominees[0]['actor'] != learner.actor):
            learner.actor_events.append(dict(step=learner.action_count, actor=deepcopy(learner.actor), status='revoked_stationary_control_hypothesis', evidence_hash=result['evidence_hash']))
            learner.knowledge_epochs.append(dict(reason='ambiguous_actor_authority', ended_by=result['evidence_hash'], knowledge=learner.memory.export(), revisions=deepcopy(learner.memory.revisions), local_endpoints=learner.memory.local_report(), suspended_global_actions=sorted(learner.memory.suspended), active_local_claim=False))
            learner.revision_history.extend(deepcopy(learner.memory.revisions))
            learner.actor = None
            learner.control_authority = False
            learner.memory = TransitionMemory()
            learner.floor_labels.clear()
            learner.blocked.clear()
            learner.blocking_labels.clear()
            learner.visits.clear()
            learner.attempts.clear()
            learner.target_rejections.clear()
            actor_before = None
            position = None
            rule_before = None
        if learner.actor is None and len(nominees) == 1:
            nominee = nominees[0]
            learner.actor = nominee['actor']
            learner.control_authority = True
            learner.actor_events.append(dict(step=learner.action_count, actor=deepcopy(learner.actor), status=nominee['status'], support=[r['evidence_hash'] for r in nominee['support']]))
            for support in nominee['support']:
                learner.floor_labels.update(support['vacated_labels'])
                learner.memory.learn(learner.ledger, support['evidence_hash'], learner.actor, allow_revision=learner.revise)
            actor_before = learner.locate_actor(current)
        if learner.actor is not None:
            if learner.control_authority:
                learner.learn_collision(current, after, actor_before, result, rule_before)
            if actor_before:
                actor_after = learner.locate_actor(after)
                occupied = {tuple(p) for p in actor_after['cells_rc']} if actor_after else {tuple(p) for p in actor_before['cells_rc']}
                for (y, x) in actor_before['cells_rc']:
                    if (y, x) not in occupied:
                        learner.floor_labels.add(after['frame'][y][x])
            revisions_before = len(learner.memory.revisions)
            learned = learner.memory.learn(learner.ledger, result['evidence_hash'], learner.actor, allow_revision=learner.revise, before=current, after=after)
            if len(learner.memory.revisions) > revisions_before:
                learner.blocked.clear()
                learner.blocking_labels.clear()
                learner.target_rejections.clear()
            if learner.control_authority and position is not None and (result['observed_delta_rc'] == [0, 0]):
                learner.blocked.add((position, action))
            elif position is not None and result['observed_delta_rc'] is not None:
                learner.blocked.discard((position, action))
        else:
            learned = dict(status='actor_not_identified')
        learner.events.append(dict(step=learner.action_count, purpose=purpose, action=action, prediction_status=result['prediction_status'], learned=learned, evidence_hash=result['evidence_hash']))

        self.current=after
        return self._offer()
