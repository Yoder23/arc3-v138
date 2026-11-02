"""Retry-local validation of retained, measured motion hypotheses.

Only global/position-conditioned motion transfers. Hidden temporal state,
surface labels and actor authority are reacquired from the new episode.
"""
from collections import defaultdict
from copy import copy, deepcopy
from evidence import digest, observation
from phase_stream import PhaseStream
from compound_planner import CompoundPlanner


def packed(memory):
    out=[]
    for (sig,action),rows in sorted(memory.rows.items()):
        if sig not in memory.moved:continue
        unique={r['evidence_hash']:r for r in rows}
        for row in list(unique.values())[-64:]:
            out.append(dict(label=sig[0],shape_rc=[list(p) for p in sig[1]],action=action,row=deepcopy(row)))
    return out[-2048:]


def unpack(rows):
    out=defaultdict(list)
    for item in rows:
        sig=(item['label'],tuple(tuple(p) for p in item['shape_rc']))
        r=deepcopy(item['row']);r['origin']=tuple(r['origin']);r['delta']=tuple(r['delta'])
        # JSON object keys must be normalized before replaying context models.
        r['parity_before']={int(k):v for k,v in r['parity_before'].items()}
        out[(sig,item['action'])].append(r)
    return out


class RetryStream(PhaseStream):
    def __init__(self,*,prior=None,**kwargs):
        super().__init__(**kwargs)
        self.prior_rows=unpack(prior['rows']) if prior else defaultdict(list)
        self.prior_digest=digest(prior) if prior else None
        self.rejected_prior=set();self.validations={};self.archive=None

    def models(self,signature):
        local=super().models(signature)
        if not self.prior_rows or self.temporal.action_contrasts(signature)<1:return local
        current=self.temporal
        # Prior proposals cannot borrow context states or observations from the
        # new episode. They propose static rules for explicit revalidation.
        old=copy(current);old.rows=defaultdict(list,{key:rows for key,rows in self.prior_rows.items() if key[0]==signature})
        self.temporal=old
        try:prior_models=CompoundPlanner.models(self,signature)
        finally:self.temporal=current
        if not prior_models or prior_models[0]['kind'] not in ('global_action','position_phase'):return local
        accepted={};evidence={}
        for action in prior_models[0]['actions']:
            key=(signature,action)
            if key in self.rejected_prior:continue
            fresh=current.rows.get(key,[]);moving=[r for r in fresh if r['delta']!=(0,0)]
            consistent=[];refuted=False
            for r in moving:
                expected=self.transition(prior_models,(0,),r['origin'],action)
                if expected is None:continue
                if expected[0]!=r['delta']:refuted=True;break
                consistent.append(r)
            if refuted:
                self.rejected_prior.add(key);continue
            if len(consistent)>=2 and len({r['origin'] for r in consistent})>=2:
                accepted[action]=prior_models[0]['actions'][action]
                evidence[action]=sorted({r['evidence_hash'] for r in consistent})
        if len(accepted)<2:return local
        # Do not use an inherited action until this episode has tested it.
        model=deepcopy(prior_models[0]);model['actions']=accepted
        model['local']={}
        for (sig,action),rows in current.rows.items():
            if sig==signature:
                for r in rows:model['local'].setdefault((action,r['origin']),set()).add(r['delta'])
        inherited=set(accepted)
        if local:
            if len(local)!=1 or local[0]['kind'] not in ('global_action','position_phase'):return local
            inherited-=set(local[0]['actions'])
            if not inherited:return local
            # Freshly inferred effects take precedence on overlapping actions.
            model['actions'].update(deepcopy(local[0]['actions']))
            model['kind']='position_phase'
        self.validations[signature]=dict(prior_digest=self.prior_digest,fresh_support=evidence,
            historical_support=sorted({r['evidence_hash'] for (sig,a),rows in self.prior_rows.items() if sig==signature and a in inherited for r in rows}),
            kind=model['kind'],actions=sorted(accepted),inherited_actions=sorted(inherited))
        return [model]

    def choose(self,obs):
        self.validations={}
        result=super().choose(obs)
        d=self.decisions[-1]
        if d['temporal']:
            sig=(d['actor']['label'],tuple(tuple(p) for p in d['actor']['shape_rc']))
            validation=self.validations.get(sig)
            used={h for edge in d['path'] if validation and edge['action'] in validation['inherited_actions'] for h in edge['support']}
            # Historical support is counted only if the actual selected path
            # used it, rather than merely evaluating a discarded hypothesis.
            if used and sig in self.validations:
                d['retry_transfer']=deepcopy(self.validations[sig]);d['retry_transfer']['used_historical_support']=sorted(used)
        d['rejected_prior_actions']=len(self.rejected_prior)
        return result

    def snapshot(self,obs):
        merged=copy(self.temporal);merged.rows=deepcopy(self.prior_rows)
        for key in self.rejected_prior:merged.rows.pop(key,None)
        for key,rows in self.temporal.rows.items():merged.rows[key].extend(deepcopy(rows))
        merged.moved={sig for (sig,a),rows in merged.rows.items() if any(r['delta']!=(0,0) for r in rows)}
        return dict(schema='measured-retry-motion-v1',level=obs['levels_completed'],
            dimensions=[len(obs['frame']),len(obs['frame'][0])],rows=packed(merged))

    def ingest(self,current,action,after):
        if after['state']!='NOT_FINISHED' or current['levels_completed']!=after['levels_completed']:
            self.archive=self.snapshot(current)
        if current['levels_completed']!=after['levels_completed']:
            self.prior_rows.clear();self.prior_digest=None;self.rejected_prior.clear()
        return super().ingest(current,action,after)


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
                self.learner=RetryStream(prior=prior,temporal=True,schedule_seed=self.seed+self.episode*1009,minimum_acquisition=8 if self.episode else 16)
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
