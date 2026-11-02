"""Observe an advisor's executed actions, then learn with explicit revalidation."""
from copy import deepcopy
from evidence import observation, digest
from observed_action_repository import ObservedActions
from inquiry_retry_session import RetrySession


class AdvisorRetrySession:
    def __init__(self, advisor, *, retain_advisor=True, advisor_budget=96,
                 seed=1610202603, max_actions=1024):
        self.advisor = advisor
        self.retain_advisor = retain_advisor
        self.advisor_budget = advisor_budget
        self.seed, self.max_actions = seed, max_actions
        self.observer = ObservedActions(max_records=advisor_budget)
        self.pending = None
        self.used = 0
        self.retry = None
        self.last_decision = None
        self.last_phase = None
        self.handoff = None

    def respond(self, raw):
        obs = observation(raw)
        if self.pending is not None:
            token, action = self.pending
            self.observer.commit(token, action, obs)
            self.pending = None
        self.last_decision = None
        if obs['state'] == 'WIN' or self.used >= self.max_actions:
            if self.retry is not None:
                self.retry.respond(obs)  # Flush the last actual transition only.
            return dict(done=True, action=0, data={}, advisor=None, certificate=None)
        if self.retry is None and (self.used >= self.advisor_budget or obs['state'] in ('GAME_OVER', 'NOT_PLAYED')):
            prior = self.observer.snapshot(obs)
            self.handoff = dict(at_action=self.used, reason='advisor_budget' if self.used >= self.advisor_budget else 'terminal',
                                retained=self.retain_advisor, prior_rows=len(prior['rows']), prior_digest=digest(prior),
                                actual_chain=self.observer.chain, level=obs['levels_completed'])
            self.retry = RetrySession(transfer=True, seed=self.seed, max_actions=self.max_actions-self.used)
            self.retry.prior = prior if self.retain_advisor else None
        if self.retry is None:
            response = self.advisor.respond(obs)
            if response['done']:
                return response
            action = response['action']
            # The advisor owns this proposal and executes exactly this action.
            token = self.observer.propose(obs, action)
            self.pending = token, action
            self.last_phase = 'advisor'
        else:
            response = self.retry.respond(obs)
            self.last_decision = deepcopy(self.retry.last_decision)
            self.last_phase = 'retry'
        if not response['done']:
            self.used += 1
        return dict(response, handoff_learning=dict(phase=self.last_phase, total_actions=self.used,
                    advisor_records=len(self.observer.rows), handoff=deepcopy(self.handoff)))
