"""Retain positive episodes while revising disproved unconditional tool rules."""
from collections import defaultdict
import copy
from completion_tool_word_learner import Learner as Base
from literal_word_rows import values, contains
from visual_transform_learner import public


class Learner(Base):
    def __init__(self, *, retain=True):
        super().__init__(retain=retain)
        self.tool_refutations = defaultdict(list)

    def observe(self, raw, action=None, data=None):
        obs = public(raw)
        previous, selected = self.previous, self.pending
        super().observe(obs, action, data)
        if previous is None or not selected or selected["phase"] != "apply":
            return
        if action != 6 or selected.get("predicted_token") is None or not selected.get("goal"):
            return
        if previous["state"] != "NOT_FINISHED" or obs["state"] != "NOT_FINISHED":
            return
        if previous["levels_completed"] != obs["levels_completed"]:
            return
        target = selected["goal"]["target"]
        before, after = values(previous["frame"], target), values(obs["frame"], target)
        if before is None or after is None:
            return
        data = data or {}
        point = (data.get("x"), data.get("y"))
        tokens = [i for i, box in enumerate(target) if contains(box, point)]
        if len(tokens) != 1:
            return
        i = tokens[0]
        predicted = selected["predicted_token"]
        if after[i] != predicted:
            control = selected["selection"]["point"]
            self.tool_refutations[target, control].append(dict(
                index=len(self.history) - 1, token=i, before=before[i], actual=after[i],
                predicted=predicted, selection=copy.deepcopy(selected["selection"])))

    def propose(self, raw):
        # Shallow projection leaves original state and every positive episode
        # untouched. Refuted controls remain available for explicit probes.
        projected = copy.copy(self)
        projected.models = {key: support for key, support in self.models.items()
            if not self.tool_refutations.get(key)}
        return Base.propose(projected, raw)
