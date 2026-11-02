"""Separate a word hypothesis from the action that might submit that word."""
from collections import Counter
import copy
from retained_tool_word_learner import Learner as Base
from literal_word_rows import values
from visual_transform_learner import public, digest


def completion_actions(obs):
    legal = set(obs["available_actions"]) - {0, 6}
    return tuple(a for a in (5, 7, 1, 2, 3, 4) if a in legal)


class Learner(Base):
    def __init__(self, *, retain=True):
        super().__init__(retain=retain)
        self.strategy_failures = Counter()
        self.completion_trials = []

    def observe(self, raw, action=None, data=None):
        obs = public(raw)
        old, selected = self.previous, self.pending
        # The original observation/causal-learning code is retained. Its older
        # global word rejection is suppressed: this class records the attempted
        # completion strategy instead.
        if selected and selected["phase"] in ("submit", "apply"):
            self.pending = dict(copy.deepcopy(selected), phase="completion_monitor")
        super().observe(obs, action, data)
        if old is None or selected is None or not selected.get("goal"):
            return
        if old["levels_completed"] != obs["levels_completed"] or old["state"] != obs["state"] or obs["state"] != "NOT_FINISHED" or action == 0:
            return
        goal = selected["goal"]
        submitted = selected["phase"] == "submit" and values(old["frame"], goal["target"]) == goal["word"]
        automatic = selected["phase"] == "apply" and not completion_actions(obs) and values(obs["frame"], goal["target"]) == goal["word"]
        if submitted or automatic:
            choice = action if submitted else None
            self.strategy_failures[self.goal_key(goal), choice] += 1
            self.completion_trials.append(dict(index=len(self.history) - 1, goal=copy.deepcopy(goal),
                completion_action=choice, automatic=automatic))

    def goals(self, obs, target):
        options = completion_actions(obs) or (None,)
        return [goal for goal in super().goals(obs, target)
                if not all(self.strategy_failures[self.goal_key(goal), a] for a in options)]

    def propose(self, raw):
        obs = public(raw)
        c = super().propose(obs)
        if c is None or c["phase"] in ("reset", "apply") or not c.get("goal"):
            return c
        goal = c["goal"]
        if values(obs["frame"], goal["target"]) != goal["word"]:
            return c
        choices = [a for a in completion_actions(obs) if not self.strategy_failures[self.goal_key(goal), a]]
        if not choices:
            return c
        return dict(kind="literal_tool_word_attempt", phase="submit", action=choices[0], data={},
            context=digest(obs), goal=copy.deepcopy(goal), evidence=[],
            scope="The visible word is complete. Test one still-untried legal completion input. A failed attempt scopes evidence to this word-plus-input strategy; the word and other completion alternatives remain remembered.")
