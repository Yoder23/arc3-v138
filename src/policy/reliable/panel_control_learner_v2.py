"""Seek a new causal context before alternating away from an unresolved selector."""
from panel_control_learner import Learner as Base
class Learner(Base):
    def propose(self,obs):
        cert=super().propose(obs)
        if not cert or cert['kind']!='discover_selection' or self.current is None:return cert
        legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7});box=self.snapshot['box'];n=len(self.snapshot['classes'])
        editors={r['action'] for r in self.edit_rows if r['box']==box}
        unknown=[a for a in legal if a not in editors]
        if not unknown:return cert
        def information(a):
            origins={r['before'] for r in self.select_rows if r['action']==a and r['box']==box and r['n']==n}
            return (int(self.current in origins),-len(origins),self.counts[a],a)
        action=min(unknown,key=information)
        support=sorted({h for r in self.select_rows if r['action']==action and r['box']==box and r['n']==n for h in r['evidence']})
        return dict(cert,action=action,selection_probe_basis='Test an unresolved selection action from a new observed origin before switching experiments.',selection_prior_support=support)
