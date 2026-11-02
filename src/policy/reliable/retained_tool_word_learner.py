"""Learn select/apply sequences and test retained visible word hypotheses.

Every pair is an experiment. A repeated effect is local evidence, not a
guaranteed prediction or a supplied goal. No game identities enter this module.
"""
from collections import Counter, defaultdict
import copy
from literal_word_rows import layouts, values, center, contains
from literal_word_goals import channels
from visual_transform_learner import public, digest


class Learner:
    def __init__(self, *, retain=True):
        self.retain = retain
        self.previous = None
        self.history = []
        self.rows = {}
        self.sources = {}
        self.edited = Counter()
        self.models = defaultdict(list)
        self.pair_trials = Counter()
        self.failed = Counter()
        self.goal_attempts = Counter()
        self.pending = None
        self.queued = None
        self.discovery = 0
        self.resets = 0
        self.refutations = []

    def clear(self):
        retain, resets = self.retain, self.resets
        self.__init__(retain=retain)
        self.resets = resets

    def observe(self, raw, action=None, data=None):
        obs = public(raw)
        old, selected = self.previous, self.pending
        data = data or {}
        if old is not None:
            boundary = obs["levels_completed"] != old["levels_completed"] or obs["state"] == "WIN"
            if boundary or action == 0 and not self.retain:
                self.clear()
            elif action is not None:
                event = dict(before=copy.deepcopy(old), action=action, data=copy.deepcopy(data), after=copy.deepcopy(obs))
                index = len(self.history)
                self.history.append(event)
                if action == 6 and old["state"] == obs["state"] == "NOT_FINISHED":
                    point = (data["x"], data["y"])
                    for row in self.rows:
                        left, right = values(old["frame"], row), values(obs["frame"], row)
                        if left is None or right is None:
                            continue
                        changed = [i for i, (a, b) in enumerate(zip(left, right)) if a != b]
                        if len(changed) != 1 or not contains(row[changed[0]], point):
                            continue
                        self.edited[row] += 1
                        if index == 0:
                            continue
                        prior = self.history[index - 1]
                        if prior["action"] != 6 or prior["after"] != old:
                            continue
                        control = (prior["data"]["x"], prior["data"]["y"])
                        if any(contains(box, control) for box in row):
                            continue
                        self.models[row, control].append(dict(select_index=index - 1, apply_index=index,
                            token=changed[0], before=left[changed[0]], after=right[changed[0]]))
                if selected and selected.get("goal") and old["state"] == obs["state"] == "NOT_FINISHED":
                    goal = selected["goal"]
                    complete = values(obs["frame"], goal["target"]) == goal["word"]
                    tested = selected["phase"] == "submit" or selected["phase"] == "apply" and 5 not in obs["available_actions"]
                    if complete and tested:
                        key = self.goal_key(goal)
                        self.failed[key] += 1
                        self.refutations.append(dict(index=index, goal=copy.deepcopy(goal)))
            if action == 0:
                self.resets += 1
                self.queued = None
        if obs["state"] != "NOT_FINISHED":
            self.queued = None
        index = len(self.history)
        for row in layouts(obs["frame"]):
            if len(self.rows) < 64:
                self.rows.setdefault(row, index)
            if row not in self.rows:
                continue
            for channel, word in channels(obs["frame"], row).items():
                if len(set(word)) >= 2 and len(self.sources) < 192:
                    self.sources.setdefault((row, channel, word), index)
        self.previous = copy.deepcopy(obs)
        self.pending = None

    @staticmethod
    def goal_key(goal):
        return goal["target"], goal["source"], goal["channel"], goal["word"]

    def goals(self, obs, target):
        result = []
        current = values(obs["frame"], target)
        if current is None:
            return result
        for (row, channel, word), index in self.sources.items():
            if row == target or len(row) != len(target) or self.edited[row]:
                continue
            goal = dict(target=target, source=row, channel=channel, word=word, observed_at=index)
            if self.failed[self.goal_key(goal)]:
                continue
            distance = sum(abs(a - b) for a, b in zip(center(target[0]), center(row[0])))
            result.append((self.goal_attempts[self.goal_key(goal)] // 16, distance, index, row, channel, word, goal))
        return [v[-1] for v in sorted(result, key=lambda v: v[:-1])]

    def propose(self, raw):
        obs = public(raw)
        if obs["state"] == "WIN":
            return None
        base = dict(kind="literal_tool_word_attempt", context=digest(obs),
            scope="A tentative visible-word goal and actual select/apply evidence guide a new experiment. No predicted success or hidden target is supplied.")
        if obs["state"] in ("NOT_PLAYED", "GAME_OVER"):
            return dict(base, phase="reset", action=0, data={}, goal=None, evidence=[])
        if 6 not in obs["available_actions"]:
            return None
        if self.queued:
            return dict(base, phase="apply", action=6, data=dict(x=self.queued["point"][0], y=self.queued["point"][1]),
                goal=copy.deepcopy(self.queued.get("goal")), evidence=copy.deepcopy(self.queued.get("evidence", [])),
                selection=copy.deepcopy(self.queued["selection"]), predicted_token=self.queued.get("predicted_token"))
        targets = [r for r in self.edited if self.edited[r] and values(obs["frame"], r) is not None]
        targets.sort(key=lambda r: (-len(r), -self.edited[r], r))
        if targets:
            target = targets[0]
            goals = self.goals(obs, target)
            goal = goals[0] if goals else None
            current = values(obs["frame"], target)
            if goal and current == goal["word"] and 5 in obs["available_actions"]:
                return dict(base, phase="submit", action=5, data={}, goal=copy.deepcopy(goal), evidence=[])
            mismatch = [i for i, value in enumerate(current) if goal and value != goal["word"][i]]
            index = mismatch[0] if mismatch else self.discovery % len(target)
            desired = goal["word"][index] if goal else None
            controls = sorted({center(box) for row in self.rows if row != target and not self.edited[row]
                for box in row if not any(contains(t, center(box)) for t in target)})
            if not controls:
                return None
            learned = []
            for point in controls:
                support = self.models.get((target, point), [])
                outputs = {r["after"] for r in support}
                if desired is not None and outputs == {desired}:
                    learned.append((-len({(s["token"], s["before"]) for s in support}), self.pair_trials[target, point], point, support))
            if learned:
                _, _, point, support = min(learned)
                evidence = copy.deepcopy(support)
            else:
                point = min(controls, key=lambda p: (self.pair_trials[target, p], p))
                evidence = []
            return dict(base, phase="select", action=6, data=dict(x=point[0], y=point[1]),
                goal=copy.deepcopy(goal), evidence=evidence, target=target,
                followup=center(target[index]), predicted_token=desired if learned else None)
        # Discover an editable word through actual pairs, without assuming which
        # row contains tools or output. The second click tests a different row.
        rows = [r for r in sorted(self.rows) if values(obs["frame"], r) is not None]
        pairs = [(a, b) for a in rows for b in rows if a != b]
        if not pairs:
            return None
        source, target = pairs[self.discovery % len(pairs)]
        token = (self.discovery // len(pairs)) % len(source)
        point = center(source[token])
        return dict(base, phase="select", action=6, data=dict(x=point[0], y=point[1]),
            goal=None, evidence=[], target=target, followup=center(target[0]), predicted_token=None)

    def commit(self, certificate):
        self.pending = copy.deepcopy(certificate)
        if certificate["phase"] == "select":
            if certificate.get("goal"):
                self.goal_attempts[self.goal_key(certificate["goal"])] += 1
            point = (certificate["data"]["x"], certificate["data"]["y"])
            self.pair_trials[certificate["target"], point] += 1
            self.discovery += 1
            self.queued = dict(point=certificate["followup"], goal=copy.deepcopy(certificate["goal"]),
                evidence=copy.deepcopy(certificate["evidence"]), predicted_token=certificate["predicted_token"],
                selection=dict(index=len(self.history), point=point))
        elif certificate["phase"] == "apply":
            self.queued = None

    def respond(self, raw):
        self.observe(raw, getattr(self, "last_action", None), getattr(self, "last_data", None))
        certificate = self.propose(raw)
        if certificate:
            self.commit(certificate)
        action = certificate["action"] if certificate else None
        data = certificate["data"] if certificate else {}
        self.last_action, self.last_data = action, copy.deepcopy(data)
        return dict(done=action is None, action=0 if action is None else action,
            data=data, certificate=certificate, advisor="retained_tool_word",
            diagnostics=dict(actual_model_calls=0, observed_events=len(self.history),
                retained_goal_sources=len(self.sources), observed_pair_effects=sum(map(len, self.models.values())),
                actual_resets=self.resets, completed_goal_refutations=len(self.refutations)))
