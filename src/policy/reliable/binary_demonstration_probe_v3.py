"""Bounded inquiry into previously untested demonstration controls.

Only visible geometric controls and actual observation changes are retained.
No command semantics or benchmark coordinates are assumed.
"""
import copy
import hashlib
import json
from collections import Counter
from binary_demonstration_bootstrap_v1 import Agent as Bootstrap, components


def digest(raw):
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def buttons(frame):
    obs = components(frame)
    marks = [o for o in obs if o['box'][2:] in ((1, 3), (3, 1))]
    if not marks:
        return []
    bottom = max(o['box'][0] + o['box'][2] for o in marks)
    return sorted([o for o in obs if o['box'][0] >= bottom and
                   5 <= o['box'][2] == o['box'][3] <= 9 and
                   .65 < len(o['shape']) / o['box'][2] ** 2 < .95 and
                   all(p in o['shape'] for p in [(0,0),(0,o['box'][3]-1),(o['box'][2]-1,0),(o['box'][2]-1,o['box'][3]-1)])], key=lambda o: o['box'])


class Agent:
    def __init__(self, prior=None):
        self.prior = prior
        self.active = True
        self.bootstrap = Bootstrap()
        self.t = 0
        self.start_level = None
        self.previous = None
        self.memory = []
        self.queue = None
        self.index = 0

    def respond(self, raw):
        if self.start_level is None:
            self.start_level = raw['levels_completed']
        if self.previous is not None:
            p = self.previous
            changes = [(y, x, a, b) for y, (r, s) in enumerate(zip(p['raw']['frame'], raw['frame']))
                       for x, (a, b) in enumerate(zip(r, s)) if a != b]
            self.memory.append(dict(source=self.t-1, before=digest(p['raw']), after=digest(raw),
                                    action=p['action'], data=p['data'], changes=changes))
            self.previous = None
        if raw['state'] != 'NOT_FINISHED':
            return dict(done=True, action=None, data={})
        if raw['levels_completed'] == self.start_level:
            result = self.bootstrap.respond(raw)
            tag = 'bootstrap_binary_inquiry'
            anchor = None
        else:
            if self.queue is None:
                controls = buttons(raw['frame'])
                if len(controls) < 2:
                    return dict(done=True, action=None, data={})
                self.controls = copy.deepcopy(controls)
                self.controls_source = self.t
                # Separate selection, repeated application, and animation hypotheses.
                self.queue = [('demonstration_control', o) for o in controls] * 2
                self.queue += [('repeat_same_demonstration_control', o) for o in controls for _ in range(2)]
            if self.index >= len(self.queue):
                return dict(done=True, action=None, data={})
            tag, anchor = self.queue[self.index]
            self.index += 1
            y, x, h, w = anchor['box']
            result = dict(done=False, action=6, data=dict(x=x+(w-1)//2, y=y+(h-1)//2))
        if result['done']:
            return result
        result['certificate'] = dict(kind='binary_demonstration_probe', source=self.t, tag=tag,
                                     anchor=anchor, anchor_source=getattr(self, 'controls_source', None),
                                     memory=copy.deepcopy(self.memory),
                                     bootstrap=result.get('certificate'))
        self.previous = dict(raw=copy.deepcopy(raw), action=result['action'], data=copy.deepcopy(result['data']))
        self.t += 1
        return result
