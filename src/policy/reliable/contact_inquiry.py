"""Revise contact hypotheses and test unmodeled controls at the contact site.

These are experiments, not assertions about an action's meaning. A failed
contact is remembered only for the same local visible context and level.
"""
from copy import deepcopy
from evidence import digest
from retry_learning import RetryStream


class ContactInquiry:
    def __init__(self):
        self.lessons = []
        self.pending = None
        self.events = []
        self.level = None

    @staticmethod
    def actor(obs, sig, parts):
        return parts(obs).get(sig)

    def applicable(self, lesson, obs, parts):
        if lesson['level'] != obs['levels_completed']:
            return False
        actor = self.actor(obs, lesson['signature'], parts)
        if actor is None:
            return False
        ignore = lesson['ignored'] | {tuple(p) for p in actor['cells_rc']}
        frame = obs['frame']
        return all(0 <= y < len(frame) and 0 <= x < len(frame[0]) and frame[y][x] == value
                   for (y,x), value in lesson['context'].items() if (y,x) not in ignore)

    def rejections(self, obs, parts):
        return {(l['target']['label'], tuple(l['target']['origin_rc']))
                for l in self.lessons if self.applicable(l, obs, parts) and set(obs['available_actions']) <= l['motion_actions'] | set(l['tried'])}

    def propose(self, obs, parts):
        l = self.pending
        if l is None:
            return None
        actor = self.actor(obs, l['signature'], parts)
        if not self.applicable(l, obs, parts) or actor is None:
            self.pending = None
            return None
        if not ({tuple(p) for p in actor['cells_rc']} & l['target_cells']):
            return None
        candidates = [a for a in obs['available_actions'] if a not in l['motion_actions'] and a not in l['tried']]
        if not candidates:
            self.pending = None
            return None
        return min(candidates), dict(contact_evidence=l['contact_evidence'], target=deepcopy(l['target']),
                                    excluded_supported_motion_actions=sorted(l['motion_actions']),
                                    already_tested=sorted(l['tried']), rationale='Test an unmodeled legal control after contact produced no progress.')

    def observe(self, before, action, after, decision, parts, models):
        h = digest(dict(before=before, action=action, after=after))
        if before['levels_completed'] != after['levels_completed'] or after['state'] != 'NOT_FINISHED':
            self.events.append(dict(kind='boundary', evidence_hash=h))
            self.lessons.clear(); self.pending = None
            return
        if decision.get('contact_inquiry'):
            l = self.pending
            assert l is not None
            l['tried'][action] = h
            self.events.append(dict(kind='interaction_test', action=action, evidence_hash=h,
                                    visible_change=before['frame'] != after['frame']))
            if not self.applicable(l, after, parts):
                self.pending = None
            return
        if not decision['temporal']:
            return
        sig = decision['actor']['label'], tuple(map(tuple, decision['actor']['shape_rc']))
        left, right = self.actor(before,sig,parts), self.actor(after,sig,parts)
        if left is None or right is None:
            return
        target = decision['target']; cells = {tuple(p) for p in target['cells_rc']}
        if not (cells & {tuple(p) for p in right['cells_rc']}) or (cells & {tuple(p) for p in left['cells_rc']}):
            return
        # Only movement supported before the action can exclude a control.
        motion = set()
        for a in before['available_actions']:
            effect = RetryStream.transition(models, tuple(m['state'] for m in models), tuple(left['origin_rc']), a) if models else None
            if effect is not None and effect[0] != (0,0):
                motion.add(a)
        y0,x0 = target['origin_rc']; radius = 4
        height=max(y for y,x in target['shape_rc'])+1; width=max(x for y,x in target['shape_rc'])+1
        ignored = cells | {tuple(p) for p in left['cells_rc']} | {tuple(p) for p in right['cells_rc']}
        context = {(y,x):after['frame'][y][x] for y in range(max(0,y0-radius), min(len(after['frame']),y0+height+radius))
                   for x in range(max(0,x0-radius), min(len(after['frame'][0]),x0+width+radius)) if (y,x) not in ignored}
        lesson = dict(level=after['levels_completed'], signature=sig, target=deepcopy(target), target_cells=cells,
                      context=context, ignored=ignored, motion_actions=motion, tried={}, contact_evidence=h)
        for old in self.lessons:
            if old['signature']==sig and old['target']['origin_rc']==target['origin_rc'] and old['target']['label']==target['label'] and self.applicable(old,after,parts):
                lesson['tried'].update(old['tried'])
        self.lessons.append(lesson); self.lessons=self.lessons[-32:]; self.pending=lesson
        self.events.append(dict(kind='contact_without_progress', evidence_hash=h, target=deepcopy(target), motion_actions=sorted(motion)))


class InquiryStream(RetryStream):
    def __init__(self, *, inquiry=True, **kwargs):
        super().__init__(**kwargs)
        self.inquiry_enabled=inquiry
        self.inquiry=ContactInquiry()
        self.pending_models=None

    def choose(self, obs):
        if self.inquiry_enabled:
            proposal=self.inquiry.propose(obs,self.temporal.parts)
            if proposal:
                action,certificate=proposal
                self.decisions.append(dict(step=self.action_count,temporal=False,action=action,prediction=None,
                    purpose='conditional_contact_experiment',contact_inquiry=certificate))
                self.pending_models=None
                return action,None,'conditional_contact_experiment'
        added=set()
        if self.inquiry_enabled:
            added=self.inquiry.rejections(obs,self.temporal.parts)-self.temporal_rejections
            self.temporal_rejections.update(added)
        result=super().choose(obs)
        self.temporal_rejections.difference_update(added)
        d=self.decisions[-1]
        self.pending_models=self.models((d['actor']['label'],tuple(map(tuple,d['actor']['shape_rc'])))) if d['temporal'] else None
        return result

    def ingest(self,current,action,after):
        d=self.decisions[-1]
        if self.inquiry_enabled:
            self.inquiry.observe(current,action,after,d,self.temporal.parts,self.pending_models)
        return super().ingest(current,action,after)
