from copy import deepcopy
from evidence import digest, observation
from resumable_inquiry_stream import InquiryStream

class RetrySession:
    """One bounded session; reset actions never become motion evidence."""
    def __init__(self,*,transfer=True,seed=1610202603,max_actions=1024):
        self.transfer=transfer;self.seed=seed;self.max_actions=max_actions
        self.used=0;self.episode=-1;self.learner=None;self.stream=None;self.prior=None
        self.resets=0;self.archive_log=[];self.chain=None;self.pending=None;self.last_decision=None
        self.actual_transitions=0;self.transferred_plans=0;self.last_result=None

    def _seal(self,obs):
        if self.pending is None:return
        before,action=self.pending
        event=dict(before=before,action=action,after=obs,previous=self.chain)
        self.chain=digest(event);self.actual_transitions+=1
        self.pending=None

    def respond(self,raw):
        obs=observation(raw);self._seal(obs);proposal=None
        if self.stream is not None:
            try:proposal=self.stream.send(obs)
            except StopIteration as done:
                self.last_result=done.value;self.stream=None
                self.prior=self.learner.archive
                self.archive_log.append(dict(episode=self.episode,level=obs['levels_completed'],state=obs['state'],
                    actions=self.learner.action_count,rows=len(self.prior['rows']) if self.prior else 0,
                    prior_digest=digest(self.prior) if self.prior else None,actual_chain=self.chain))
        if obs['state']=='WIN':return dict(done=True,action=0,data={},advisor=None,certificate=None)
        if self.used>=self.max_actions:return dict(done=True,action=0,data={},advisor=None,certificate=None)
        if obs['state'] in ('GAME_OVER','NOT_PLAYED'):
            self.resets+=1;action=0;self.last_decision=None
        else:
            if self.stream is None:
                self.episode+=1;prior=self.prior if self.transfer else None
                if prior and (prior['level']!=obs['levels_completed'] or prior['dimensions']!=[len(obs['frame']),len(obs['frame'][0])]):prior=None
                self.learner=InquiryStream(prior=prior,temporal=True,schedule_seed=self.seed+self.episode*1009,minimum_acquisition=8 if self.episode else 16)
                self.stream=self.learner.interact(obs,max_actions=self.max_actions-self.used)
                proposal=next(self.stream)
            action=proposal['action'];self.last_decision=deepcopy(self.learner.decisions[-1])
            self.transferred_plans+=int('retry_transfer' in self.last_decision)
            assert action in obs['available_actions']
        self.used+=1;self.pending=(deepcopy(obs),action)
        return dict(done=False,action=action,data={},advisor='retry',certificate=None,
            diagnostics=dict(actions=self.used,episode=self.episode,resets=self.resets,
                latent_plan=bool(self.last_decision and self.last_decision['temporal']),
                transfer_plan=bool(self.last_decision and 'retry_transfer' in self.last_decision),
                transferred_plans=self.transferred_plans,archived_attempts=len(self.archive_log),actual_model_calls=0))
