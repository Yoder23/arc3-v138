"""Small model-based learner for translated-object curricula, not a general ARC agent.

Perception, shortest-path search and object-contact goal hypotheses are authored
priors. Action displacements, blocked edges and their revisions come from actual
public interaction. The only environment access is a step callback.
"""
from collections import Counter, deque
from copy import deepcopy
from evidence import EvidenceLedger, components, primitive_components, observation
from composite_components import palette
from knowledge import TransitionMemory
from control_hypotheses import ControlHypotheses
import random


class ReliableLearner:
    def __init__(self, prior=None, *, revise=True):
        if not revise:raise ValueError('Conditional memory currently requires revision; frozen ablation is unsupported')
        self.memory=TransitionMemory(prior);self.ledger=EvidenceLedger();self.revise=revise
        self.actor=None;self.control_authority=False;self.floor_labels=set();self.blocked=set();self.visits=Counter();self.attempts=Counter()
        self.events=[];self.action_count=0;self.target_rejections=set()
        self.control_hypotheses=ControlHypotheses();self.actor_events=[]
        self.blocking_labels={};self.collision_events=[]
        self.knowledge_epochs=[];self.revision_history=[]

    def reset_scene(self,reason,evidence_hash):
        # Historical measurements remain addressable. They are not current
        # controls, and must be explicitly retrieved as unverified priors.
        self.knowledge_epochs.append(dict(reason=reason,ended_by=evidence_hash,
            knowledge=self.memory.export(),revisions=deepcopy(self.memory.revisions),
            local_endpoints=self.memory.local_report(),suspended_global_actions=sorted(self.memory.suspended),active_local_claim=False))
        if self.actor is not None:
            self.actor_events.append(dict(step=self.action_count,actor=deepcopy(self.actor),
                status=reason,evidence_hash=evidence_hash))
        self.revision_history.extend(deepcopy(self.memory.revisions));self.actor=None;self.control_authority=False;self.memory=TransitionMemory();self.control_hypotheses=ControlHypotheses()
        self.floor_labels.clear();self.blocked.clear();self.blocking_labels.clear()
        self.visits.clear();self.attempts.clear();self.target_rejections.clear()

    def locate_actor(self, obs):
        if self.actor is None:return None
        candidates=[c for c in components(obs['frame']) if c['label']==self.actor['label'] and c['shape_rc']==self.actor['shape_rc']]
        return candidates[0] if len(candidates)==1 else None

    def targets(self, obs):
        # A testable object-contact prior, not a supplied goal label.
        total=len(obs['frame'])*len(obs['frame'][0])
        return [c for c in primitive_components(obs['frame']) if c['label'] not in self.floor_labels|palette(self.actor['label'])|set(self.blocking_labels)
                and c['size']<total/4 and (c['label'],tuple(c['origin_rc'])) not in self.target_rejections]

    def route(self, obs, actor, target):
        start=tuple(actor['origin_rc']);goal={tuple(p) for p in target['cells_rc']}
        allowed=self.floor_labels|palette(actor['label'])|{target['label']};frame=obs['frame'];height,width=len(frame),len(frame[0])
        def fits(p):
            return all(0<=p[0]+dy<height and 0<=p[1]+dx<width and frame[p[0]+dy][p[1]+dx] in allowed-set(self.blocking_labels)
                       for dy,dx in actor['shape_rc'])
        def reached(p):return any((p[0]+dy,p[1]+dx) in goal for dy,dx in actor['shape_rc'])
        queue=deque([start]);paths={start:[]}
        while queue:
            here=queue.popleft()
            if reached(here):return paths[here]
            for action in obs['available_actions']:
                rule=self.memory.prediction(action, here)
                if rule is None or (here,action) in self.blocked:continue
                dy,dx=rule['delta_rc'];next_pos=(here[0]+dy,here[1]+dx)
                if next_pos not in paths and fits(next_pos):
                    paths[next_pos]=paths[here]+[action];queue.append(next_pos)
        return None

    def choose(self, obs):
        legal=obs['available_actions'];actor=self.locate_actor(obs)
        if not legal:raise RuntimeError('No legal action')
        if actor is None:
            order=list(legal);random.Random(31705619+self.action_count//len(legal)).shuffle(order)
            return min(legal,key=lambda a:(self.attempts[(None,a)],order.index(a))),None,'test_action_dependent_appearance'
        position=tuple(actor['origin_rc']);self.visits[position]+=1
        candidates=[]
        for target in (self.targets(obs) if self.control_authority else []):
            path=self.route(obs,actor,target)
            if path==[]:
                self.target_rejections.add((target['label'],tuple(target['origin_rc'])))
            elif path:
                candidates.append((len(path),path[0],target))
        if candidates:
            _,action,target=min(candidates,key=lambda x:(x[0],x[1]))
            purpose='test_object_contact_goal'
        else:
            # Probe unknown or locally unverified controls first; no fixed direction mapping.
            def priority(a):
                rule=self.memory.prediction(a, position)
                unknown=rule is None
                attempted=self.attempts[(position,a)]
                next_visits=0 if unknown else self.visits[(position[0]+rule['delta_rc'][0],position[1]+rule['delta_rc'][1])]
                return (attempted,not unknown,(position,a) in self.blocked,next_visits,a)
            action=min(legal,key=priority);purpose='discriminate_transition_hypotheses'
        rule=self.memory.prediction(action, position)
        prediction=None if rule is None else dict(label=actor['label'],shape_rc=actor['shape_rc'],delta_rc=rule['delta_rc'])
        return action,prediction,purpose

    def learn_collision(self,before,after,actor_before,result,rule_before):
        """A blocked well-measured control supports a revisable material prior.

        Same color is only a working material hypothesis within this episode.
        It is not exported as a universal property or a verified goal rule.
        """
        if actor_before is None or not result['measurement']['comparable'] or result['measurement']['boundary']:return
        # Measured entry can refute a material belief even when the action had
        # no prediction. Forecast verdicts and measured effects are distinct.
        motions=[m for m in result['measurement']['motions'] if m['label']==self.actor['label']
                 and m['shape_rc']==self.actor['shape_rc']]
        actual=motions[0]['delta_rc'] if len(motions)==1 else None
        if actual is None:
            stationary=self.locate_actor(after)
            if stationary and stationary['cells_rc']==actor_before['cells_rc']:actual=[0,0]
        evidence=result['evidence_hash']
        if actual is not None and actual!=[0,0]:
            moved=self.locate_actor(after)
            if moved:
                previous_cells={tuple(p) for p in actor_before['cells_rc']}
                entered={before['frame'][y][x] for y,x in moved['cells_rc'] if (y,x) not in previous_cells}
                for label in entered&set(self.blocking_labels):
                    rejected=self.blocking_labels.pop(label)
                    self.collision_events.append(dict(kind='collision_hypothesis_refuted',label=label,
                        previous_evidence=rejected,evidence_hash=evidence))
            return
        if actual!=[0,0] or rule_before is None or rule_before.get('status') in ('supported_local_endpoint','measured_periodic_endpoint_hypothesis') or len(rule_before['local_evidence'])<2:return
        dy,dx=rule_before['delta_rc'];y,x=actor_before['origin_rc'];f=before['frame']
        proposed=[(y+dy+r,x+dx+c) for r,c in actor_before['shape_rc']]
        if any(not (0<=r<len(f) and 0<=c<len(f[0])) for r,c in proposed):return
        labels={f[r][c] for r,c in proposed}-(self.floor_labels|palette(self.actor['label']))
        if len(labels)==1:
            label=next(iter(labels));self.blocking_labels.setdefault(label,[]).append(evidence)
            self.collision_events.append(dict(kind='provisional_same_label_collision',label=label,
                evidence_hash=evidence,assumptions=['currently stable controls','no unobserved action precondition','same label has same collision role']))

    def interact(self, initial, *, max_actions=128):
        if type(max_actions) is not int or max_actions<1:raise ValueError('Positive action budget required')
        current=observation(initial)
        while current['state']=='NOT_FINISHED' and self.action_count<max_actions:
            action,prediction,purpose=self.choose(current)
            actor_before=self.locate_actor(current)
            rule_before=self.memory.prediction(action, actor_before['origin_rc'] if actor_before else None)
            position=tuple(actor_before['origin_rc']) if actor_before else None
            self.attempts[(position,action)]+=1
            self.ledger.predict(current,action,prediction)
            self.action_count+=1  # An attempted callback remains charged if it fails.
            after=observation((yield dict(action=action,data={})))
            result=self.ledger.observe(after)
            if result['measurement']['boundary'] or not result['measurement']['comparable']:
                self.reset_scene('scene_boundary_or_noncomparable',result['evidence_hash'])
                self.events.append(dict(step=self.action_count,purpose=purpose,action=action,
                    prediction_status=result['prediction_status'],learned=dict(status='no_cross_boundary_learning'),
                    evidence_hash=result['evidence_hash']))
                current = after
                break
            self.control_hypotheses.update(self.ledger,result['evidence_hash'],current,after)
            nominees=self.control_hypotheses.nominate(after)
            self.control_authority=bool(len(nominees)==1 and (self.actor is None or nominees[0]['actor']==self.actor))
            if self.actor is not None and self.locate_actor(after) is None:
                self.reset_scene('actor_localization_unknown',result['evidence_hash'])
                nominees=[];actor_before=None;position=None;rule_before=None
            if self.actor is not None and not nominees:
                # Stable appearance tracking survives a failed constant-displacement
                # hypothesis. This event is not a renewed claim of causal authority.
                if not self.actor_events or self.actor_events[-1]['status'] != 'appearance_retained_control_model_uncertain':
                    self.actor_events.append(dict(step=self.action_count,actor=deepcopy(self.actor),
                        status='appearance_retained_control_model_uncertain',evidence_hash=result['evidence_hash']))
            if self.actor is not None and nominees and (len(nominees)!=1 or nominees[0]['actor']!=self.actor):
                self.actor_events.append(dict(step=self.action_count,actor=deepcopy(self.actor),
                    status='revoked_stationary_control_hypothesis',evidence_hash=result['evidence_hash']))
                self.knowledge_epochs.append(dict(reason='ambiguous_actor_authority',ended_by=result['evidence_hash'],
                    knowledge=self.memory.export(),revisions=deepcopy(self.memory.revisions),
                    local_endpoints=self.memory.local_report(),suspended_global_actions=sorted(self.memory.suspended),active_local_claim=False))
                self.revision_history.extend(deepcopy(self.memory.revisions));self.actor=None;self.control_authority=False;self.memory=TransitionMemory();self.floor_labels.clear();self.blocked.clear()
                self.blocking_labels.clear()
                self.visits.clear();self.attempts.clear();self.target_rejections.clear();actor_before=None;position=None;rule_before=None
            if self.actor is None and len(nominees)==1:
                nominee=nominees[0];self.actor=nominee['actor'];self.control_authority=True
                self.actor_events.append(dict(step=self.action_count,actor=deepcopy(self.actor),status=nominee['status'],
                    support=[r['evidence_hash'] for r in nominee['support']]))
                # Bootstrap only from actually recorded measurements of the
                # nominated appearance. No supplied control map or hidden state.
                for support in nominee['support']:
                    self.floor_labels.update(support['vacated_labels'])
                    self.memory.learn(self.ledger,support['evidence_hash'],self.actor,allow_revision=self.revise)
                actor_before=self.locate_actor(current)
            if self.actor is not None:
                if self.control_authority:self.learn_collision(current,after,actor_before,result,rule_before)
                if actor_before:
                    actor_after=self.locate_actor(after)
                    occupied={tuple(p) for p in actor_after['cells_rc']} if actor_after else {tuple(p) for p in actor_before['cells_rc']}
                    for y,x in actor_before['cells_rc']:
                        if (y,x) not in occupied:
                            self.floor_labels.add(after['frame'][y][x])
                revisions_before=len(self.memory.revisions)
                learned=self.memory.learn(self.ledger,result['evidence_hash'],self.actor,allow_revision=self.revise,before=current,after=after)
                if len(self.memory.revisions)>revisions_before:
                    self.blocked.clear();self.blocking_labels.clear();self.target_rejections.clear()
                if self.control_authority and position is not None and result['observed_delta_rc']==[0,0]:
                    self.blocked.add((position,action))
                elif position is not None and result['observed_delta_rc'] is not None:
                    self.blocked.discard((position,action))
            else:learned=dict(status='actor_not_identified')
            self.events.append(dict(step=self.action_count,purpose=purpose,action=action,
                                    prediction_status=result['prediction_status'],learned=learned,evidence_hash=result['evidence_hash']))
            current=after
        assert self.ledger.verify()
        return dict(won=current['state']=='WIN',actions=self.action_count,final_state=current['state'],
                    stop_reason='terminal' if current['state']!='NOT_FINISHED' else 'action_budget',
                    learned_knowledge=self.memory.export(),revisions=deepcopy(self.revision_history+self.memory.revisions),
                    refuted_predictions=sum(e['prediction_status']=='refuted' for e in self.events),
                    events=deepcopy(self.events),evidence=self.ledger.rows,actual_model_calls=0,
                    actor_hypotheses=deepcopy(self.actor_events),
                    collision_hypotheses=deepcopy(self.collision_events),
                    historical_knowledge_epochs=deepcopy(self.knowledge_epochs),
                    local_endpoint_table=self.memory.local_report(),
                    current_control_authority=self.control_authority,
                    public_score=False,scope='authored_translation_worlds_only')
