"""Immutable episodes; softmax associative retrieval with inferred context hypotheses."""
from dataclasses import dataclass, asdict
import numpy as np


@dataclass(frozen=True)
class Episode:
    step: int
    context: int
    action: int
    position: tuple
    delta: tuple
    mask: tuple


class AssociativeMemory:
    def __init__(self, contextual=True):
        self.records = ()
        self.contextual = contextual
        self.active = 0
        self.contexts = [0]
        self.reliability = .5
        self.events = []

    def _read(self, position, context, base):
        mean = base.copy(); variance = np.full((6,3),4.,dtype=np.float64)
        support = np.zeros((6,3),dtype=np.float64)
        for a in range(6):
            rows = [r for r in self.records if r.action==a and (not self.contextual or r.context==context)]
            if not rows:
                continue
            pos = np.asarray([r.position for r in rows]); vals = np.asarray([r.delta for r in rows]); mask = np.asarray([r.mask for r in rows])
            # Continuous positional similarity allows state-conditional recall.
            distance = np.mean(((pos-position)/12.)**2,axis=1)
            logits = -distance + np.linspace(-.5,0,len(rows))
            weight = np.exp(logits-logits.max())[:,None]*mask
            counts = weight.sum(0)
            got = counts>1e-8
            estimate = np.sum(weight*vals,axis=0)/np.maximum(counts,1e-8)
            var = np.sum(weight*(vals-estimate)**2,axis=0)/np.maximum(counts,1e-8)
            mean[a,got] = estimate[got]
            variance[a,got] = var[got]+1./(1.+counts[got])
            support[a] = counts
        return mean, variance, support

    def predict(self, position, base):
        return self._read(position, self.active, base)

    def observe(self, position, action, delta, mask, step, predicted):
        if not np.any(mask):
            return {'event':'unobserved','context':self.active}
        residual = float(np.mean((predicted[action,mask]-delta[mask])**2))
        self.reliability = .9*self.reliability+.1*float(residual<.6)
        chosen = self.active; event='update'
        if self.contextual:
            candidates=[]
            for context in self.contexts:
                mean, var, support = self._read(position,context,np.zeros((6,3)))
                valid = mask & (support[action]>.1)
                if np.all(valid[mask]):
                    error = float(np.mean((mean[action,mask]-delta[mask])**2))
                    candidates.append((error,context))
            active = next((e for e,c in candidates if c==self.active), None)
            compatible = sorted((e,c) for e,c in candidates if e<.45)
            if active is not None and active>1.1:
                if compatible:
                    chosen = compatible[0][1]; event='retrieve_context'
                else:
                    chosen = max(self.contexts)+1; self.contexts.append(chosen); event='branch_context'
                self.active = chosen
        before = self.records
        self.records = before+(Episode(step,chosen,action,tuple(position.tolist()),tuple(delta.tolist()),tuple(mask.tolist())),)
        assert self.records[:-1] == before
        result={'event':event,'context':chosen,'prior_error':residual,'reliability':self.reliability}
        self.events.append(result)
        return result

    def export(self):
        return [asdict(r) for r in self.records]
