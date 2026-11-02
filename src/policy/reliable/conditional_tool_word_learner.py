"""Compose observed input-conditioned token transitions without deleting episodes."""
from collections import defaultdict, deque
import copy
from refuted_tool_word_learner import Learner as Base
from literal_word_rows import values, contains, center
from visual_transform_learner import public


class Learner(Base):
    def __init__(self, *, retain=True):
        super().__init__(retain=retain)
        self.conditional_trials = defaultdict(list)

    def observe(self, raw, action=None, data=None):
        obs = public(raw)
        old = self.previous
        super().observe(obs, action, data)
        if old is None or action != 6 or len(self.history) < 2:
            return
        if old['state'] != obs['state'] or obs['state'] != 'NOT_FINISHED' or old['levels_completed'] != obs['levels_completed']:
            return
        prev = self.history[-2]
        if prev['action'] != 6 or prev['after'] != old:
            return
        control = prev['data']['x'], prev['data']['y']
        point = data['x'], data['y']
        for row in self.rows:
            before, after = values(old['frame'], row), values(obs['frame'], row)
            if before is None or after is None or any(contains(box, control) for box in row):
                continue
            tokens = [i for i, box in enumerate(row) if contains(box, point)]
            if len(tokens) != 1:
                continue
            token = tokens[0]
            if any(a != b for i, (a, b) in enumerate(zip(before, after)) if i != token):
                continue
            self.conditional_trials[row, control].append(dict(select_index=len(self.history)-2,
                apply_index=len(self.history)-1, token=token, before=before[token], after=after[token]))

    def propose(self, raw):
        obs = public(raw)
        c = super().propose(obs)
        if c is None or c['phase'] == 'reset' or not c.get('goal'):
            return c
        if c['phase'] == 'apply':
            context = self.queued.get('conditional_context') if self.queued else None
            if context:
                current = values(obs['frame'], c['goal']['target'])
                if current is None or current[context['token']] != context['before_token']:
                    c.update(evidence=[], predicted_token=None)
                else:
                    c['conditional_context'] = copy.deepcopy(context)
            return c
        if c['phase'] != 'select' or c.get('evidence'):
            return c
        target, goal = c['target'], c['goal']
        current = values(obs['frame'], target)
        mismatch = [i for i, (a, b) in enumerate(zip(current, goal['word'])) if a != b]
        if not mismatch:
            return c
        token = mismatch[0]
        start, desired = current[token], goal['word'][token]
        controls = sorted({center(box) for row in self.rows if row != target and not self.edited[row]
            for box in row if not any(contains(t, center(box)) for t in target)})
        edges = defaultdict(list)
        for control in controls:
            records = self.conditional_trials.get((target, control), [])
            groups = defaultdict(list)
            for r in records:
                groups[r['before']].append(r)
            for color, support in groups.items():
                outcomes = {r['after'] for r in support}
                if len(outcomes) == 1 and next(iter(outcomes)) != color:
                    edges[color].append((next(iter(outcomes)), control, support))
        frontier, seen, path = deque([(start, [])]), {start}, None
        while frontier:
            color, route = frontier.popleft()
            if color == desired:
                path = route
                break
            for output, control, support in sorted(edges[color]):
                if output not in seen:
                    seen.add(output)
                    frontier.append((output, route + [(color, output, control, support)]))
        if path:
            color, output, control, support = path[0]
            c.update(data=dict(x=control[0], y=control[1]), followup=center(target[token]),
                predicted_token=output, evidence=copy.deepcopy(support),
                conditional_context=dict(before_token=color, token=token, planned_steps=len(path),
                    hypothesis='Observed token-input conditional rule; selection may still be context-dependent.'))
        elif controls:
            # Explore a control in the current input context, not only by its
            # total lifetime usage. No outcome is invented for this probe.
            control = min(controls, key=lambda p: (
                sum(r['before'] == start for r in self.conditional_trials.get((target, p), [])),
                self.pair_trials[target, p], p))
            c.update(data=dict(x=control[0], y=control[1]), followup=center(target[token]),
                predicted_token=None, evidence=[])
        return c

    def commit(self, certificate):
        super().commit(certificate)
        if certificate['phase'] == 'select' and certificate.get('conditional_context'):
            self.queued['conditional_context'] = copy.deepcopy(certificate['conditional_context'])
