"""Prospective experience journal: learn the committed action, never a proposal."""
from copy import copy,deepcopy
from evidence import observation,digest
from phase_effect_memory import Memory
from retry_learning import packed,unpack

class ObservedActions:
    def __init__(self,max_records=4096):
        self.max_records=max_records;self.rows=[];self.chain=None;self.pending=None
        self.last=None;self.memory=Memory(True);self.prior=None;self.resets=0

    def propose(self,raw,proposed_action):
        before=observation(raw)
        if self.pending is not None:raise ValueError('Previous action has not been committed')
        if len(self.rows)>=self.max_records:raise ValueError('Journal capacity reached')
        if self.last is not None and before!=self.last:raise ValueError('Observation continuity broken')
        legal=before['available_actions'] if before['state']=='NOT_FINISHED' else [0]
        if proposed_action not in legal:raise ValueError('Illegal proposal')
        self.pending=dict(before=deepcopy(before),proposed_action=proposed_action,previous=self.chain)
        return digest(self.pending)

    def snapshot(self,before):
        merged=copy(self.memory)
        merged.rows=unpack(self.prior['rows']) if self.prior else unpack([])
        for key,rows in self.memory.rows.items():merged.rows[key].extend(deepcopy(rows))
        merged.moved={sig for (sig,a),rows in merged.rows.items() if any(r['delta']!=(0,0) for r in rows)}
        return dict(schema='measured-retry-motion-v1',level=before['levels_completed'],
            dimensions=[len(before['frame']),len(before['frame'][0])],rows=packed(merged))

    def commit(self,token,actual_action,raw_after):
        if self.pending is None or digest(self.pending)!=token:raise ValueError('Missing or wrong proposal token')
        before=self.pending['before'];after=observation(raw_after)
        legal=before['available_actions'] if before['state']=='NOT_FINISHED' else [0]
        if actual_action not in legal:raise ValueError('Illegal executed action')
        boundary=after['state']!='NOT_FINISHED' or before['levels_completed']!=after['levels_completed']
        same_shape=[len(before['frame']),len(before['frame'][0])]==[len(after['frame']),len(after['frame'][0])]
        if actual_action==0:
            if before['state'] not in ('GAME_OVER','NOT_PLAYED'):raise ValueError('Reset not at a terminal boundary')
            self.resets+=1;self.memory=Memory(True)
            if self.prior and (self.prior['level']!=after['levels_completed'] or self.prior['dimensions']!=[len(after['frame']),len(after['frame'][0])]):self.prior=None
        elif boundary or not same_shape:
            self.prior=self.snapshot(before) if before['levels_completed']==after['levels_completed'] and same_shape else None
            self.memory=Memory(True)
        else:
            # Only the action actually applied to the world labels this row.
            self.memory.observe(before,actual_action,after)
        event=dict(self.pending,actual_action=actual_action,after=deepcopy(after));event['hash']=digest(event)
        self.rows.append(event);self.chain=event['hash'];self.last=deepcopy(after);self.pending=None
        return event['hash']

    def measured_prior(self,raw):
        obs=observation(raw)
        if self.prior and self.prior['level']==obs['levels_completed'] and self.prior['dimensions']==[len(obs['frame']),len(obs['frame'][0])]:return deepcopy(self.prior)
        return None

    def export(self):
        if self.pending is not None:raise ValueError('Cannot archive an uncommitted proposal')
        return dict(schema='committed-action-journal-v1',max_records=self.max_records,events=deepcopy(self.rows),chain=self.chain)

    @classmethod
    def restore(cls,archive,expected_digest):
        if digest(archive)!=expected_digest or set(archive)!={'schema','max_records','events','chain'} or archive['schema']!='committed-action-journal-v1':raise ValueError('Untrusted or incompatible archive')
        result=cls(archive['max_records'])
        for row in archive['events']:
            if set(row)!={'before','proposed_action','previous','actual_action','after','hash'}:raise ValueError('Unexpected event fields')
            token=result.propose(row['before'],row['proposed_action']);result.commit(token,row['actual_action'],row['after'])
            if result.rows[-1]!=row:raise ValueError('Recorded transition chain differs')
        if result.chain!=archive['chain']:raise ValueError('Final chain differs')
        return result
