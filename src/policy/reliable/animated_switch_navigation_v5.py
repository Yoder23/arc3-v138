"""Observation-driven navigation, blocked-route revision and switch inquiry.

Visual priors: a square body with a center hole, a matching outlined target,
and connected colored control markings. Effects and strides are measured.
No game identifiers, level layouts or recorded action sequences are used.
"""
import copy
import hashlib
import json
from collections import Counter, deque
from binary_demonstration_bootstrap_v1 import components


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def scene(frame):
    obs = components(frame)
    actors = [o for o in obs if o['box'][0] >= 7 and 3 <= o['box'][2] == o['box'][3] <= 9
              and o['box'][2] % 2 == 1 and len(o['shape']) == o['box'][2]**2 - 1
              and (o['box'][2]//2, o['box'][3]//2) not in o['shape']]
    bindings = []
    for a in actors:
        n = a['box'][2]
        goals = [o for o in obs if o['ink'] == a['ink'] and o['box'][0] >= 7
                 and o['box'][2:] == (n+2, n+2) and len(o['shape']) < (n+2)**2//2]
        if len(goals) == 1:bindings.append((a, goals[0]))
    if len(bindings) != 1:
        return None
    a, g = bindings[0]; y, x, n, _ = a['box']
    return dict(actor=a, goal=g, target=(g['box'][0]+1, g['box'][1]+1),
                floor=frame[y+n//2][x+n//2], outside=frame[0][0], other_bodies=[o for o in actors if o != a])


def poses(raw, identity):
    result = []
    for frame in raw.get('animation_frames', [raw['frame']]):
        found = [o for o in components(frame) if o['ink'] == identity['ink']
                 and o['shape'] == identity['shape']]
        result.append(found[0] if len(found) == 1 else None)
    return result


def paths(frame, s, moves, blocked):
    start = tuple(s['actor']['box'][:2]); n = s['actor']['box'][2]
    queue = deque([start]); parents = {start: None}
    while queue and len(parents) < 512:
        y, x = queue.popleft()
        for action, (dy, dx) in sorted(moves.items()):
            if ((y, x), action) in blocked:
                continue
            q = y+dy, x+dx
            if q in parents or not (7 <= q[0] < 63-n and 0 <= q[1] <= 64-n):
                continue
            # A colored control may overlay floor. Its passability is a hypothesis
            # until an actual transition confirms it. Black outside is excluded.
            if any(frame[yy][xx] == s['outside'] for yy in range(q[0], q[0]+n)
                   for xx in range(q[1], q[1]+n)):
                continue
            parents[q] = ((y, x), action); queue.append(q)
    return parents


def route(parents, target):
    if target not in parents:
        return None
    result = []; q = target
    while parents[q] is not None:
        q, action = parents[q]; result.append(action)
    return list(reversed(result))


def compact_controls(raw, s, parents, trials):
    visited = {tuple(q['position']) for q in trials};n=s['actor']['box'][2];result=[]
    for q in parents:
        if q in visited or q==tuple(s['actor']['box'][:2]) or q==tuple(s['target']):continue
        y,x=q;core={raw['frame'][yy][xx] for yy in range(y+1,y+n-1) for xx in range(x+1,x+n-1)}
        if len(core)!=1:continue
        ink=next(iter(core))
        if ink in {s['floor'],s['actor']['ink'],s['outside']}|{o['ink'] for o in s['other_bodies']}:continue
        count=sum(raw['frame'][yy][xx]==ink for yy in range(y,y+n) for xx in range(x,x+n))
        if count>(n-2)**2+n:continue
        follow=route(parents,q)
        if follow:result.append((len(follow),q,follow))
    return sorted(result)


class Agent:
    def __init__(self, prior=None):
        self.prior = prior; self.active = True; self.previous = None; self.last = None
        self.t = 0; self.level = None; self.moves = {}; self.transitions = []
        self.failures = []; self.edges = {}; self.tried = {}; self.blocked = {}
        self.cue_trials = []; self.cue = None; self.pending_revision = None
        self.revisions = []; self.archive = []; self.mode_trials = set()

    def respond(self, raw):
        s = scene(raw['frame'])
        if raw['state'] != 'NOT_FINISHED' or s is None:
            return dict(done=True, action=None, data={})
        if self.level != raw['levels_completed']:
            if self.level is not None:
                self.archive.append(dict(level=self.level, transitions=copy.deepcopy(self.transitions),
                                         failures=copy.deepcopy(self.failures), revisions=copy.deepcopy(self.revisions)))
            self.level = raw['levels_completed']; self.previous = None
            self.edges = {}; self.tried = {}; self.blocked = {}; self.cue_trials = []
            self.cue = None; self.pending_revision = None; self.mode_trials = set()
        pos = tuple(s['actor']['box'][:2])
        # Visible control changes delimit conditional edges. Actor motion and the
        # progress bar are excluded; a new control context permits another test.
        control_pixels = [(y, x, v) for y, row in enumerate(raw['frame'][7:63], 7)
                          for x, v in enumerate(row)
                          if v not in (s['floor'], s['actor']['ink'], s['outside']) and v not in {o['ink'] for o in s['other_bodies']}]
        mode = digest([raw['frame'][:7], control_pixels])
        if self.previous:
            old = self.previous; before = old['scene']; start = tuple(before['actor']['box'][:2])
            dy, dx = pos[0]-start[0], pos[1]-start[1]
            record = dict(source=self.t-1, action=self.last, before=before['actor'], after=s['actor'],
                          before_digest=digest(old['raw']), after_digest=digest(raw),
                          mode_before=old['mode'], mode_after=mode, delta=(dy, dx),
                          animation_poses=poses(raw, before['actor']))
            self.transitions.append(record)
            self.edges.setdefault((old['mode'], start), {})[self.last] = (mode, pos)
            if self.last in (1, 2, 3, 4):
                if (dy == 0) != (dx == 0) and abs(dy)+abs(dx) <= 12:
                    self.moves[self.last] = (dy, dx)
                elif (dy, dx) == (0, 0):
                    self.blocked.setdefault(old['mode'], set()).add((start, self.last))
                    self.failures.append(dict(source=self.t-1, kind='no_motion', position=start,
                                              action=self.last, context=old['mode']))
            elif self.last == 5:
                self.revisions.append(dict(source=self.t-1, kind='nonlocal_action_outcome',
                                           returned_to=start == pos, before=start, after=pos,
                                           context_changed=mode != old['mode'], semantics_unproven=True))
        blocked = self.blocked.get(mode, set()); parents = paths(raw['frame'], s, self.moves, blocked)
        goal_path = route(parents, tuple(s['target']))
        action = None; tag = 'learn_direction_effect'; hypothesis = None
        if goal_path and self.cue is not None and pos != self.cue:
            self.revisions.append(dict(source=self.t, kind='goal_route_reopened', abandoned_cue=self.cue))
            self.cue = None
        if self.pending_revision is not None:
            action = 5; tag = 'test_control_then_nonlocal_action'; hypothesis = self.pending_revision
            self.pending_revision = None
        elif self.cue is not None:
            if pos == self.cue:
                self.cue_trials.append(dict(source=self.t, position=pos, context=mode))
                self.pending_revision = dict(control=pos, rationale='Test whether action5 preserves a control effect while changing position.')
                self.cue = None
                if 5 in raw['available_actions']:
                    action = 5; tag = 'test_control_then_nonlocal_action'; hypothesis = self.pending_revision
                    self.pending_revision = None
            else:
                follow = route(parents, self.cue)
                if follow:action = follow[0]; tag = 'approach_alternative_control'
                else:self.cue = None
        if action is None and self.archive:
            controls=compact_controls(raw,s,parents,self.cue_trials)
            if controls:
                _,self.cue,follow=controls[0];action=follow[0];tag='transfer_prior_control_intervention'
        if action is None and goal_path:
            action = goal_path[0]; tag = 'test_observed_motion_to_goal'
        if action is None and len(self.moves) >= 3:
            candidates = []
            n = s['actor']['box'][2]; visited = {tuple(q['position']) for q in self.cue_trials}
            for q in parents:
                if q in visited or q == pos or q == tuple(s['target']):continue
                y, x = q
                inks = Counter(raw['frame'][yy][xx] for yy in range(y, y+n) for xx in range(x, x+n)
                               if raw['frame'][yy][xx] not in (s['floor'], s['actor']['ink'], s['outside']) and raw['frame'][yy][xx] not in {o['ink'] for o in s['other_bodies']})
                # Dense control patches; thin decorative/wiring lines are not enough.
                if inks and max(inks.values()) >= n+3:
                    candidate = route(parents, q)
                    if candidate:candidates.append((len(candidate), q, candidate))
            if candidates:
                _, self.cue, follow = min(candidates); action = follow[0]; tag = 'approach_alternative_control'
        key = mode, pos
        if action is None:
            unknown = [a for a in (1, 2, 3, 4) if a in raw['available_actions'] and a not in self.tried.get(key, set())]
            if unknown:action = min(unknown,key=lambda a:(a in self.moves,a))
            else:
                queue = deque([(key, [])]); seen = {key}
                while queue and action is None:
                    here, path = queue.popleft()
                    if path and any(a not in self.tried.get(here, set()) for a in (1, 2, 3, 4)):
                        action = path[0]; tag = 'revisit_unexplored_state'; break
                    for a, dest in sorted(self.edges.get(here, {}).items()):
                        if dest not in seen:seen.add(dest); queue.append((dest, path+[a]))
        if action is None or self.t >= 256:
            return dict(done=True, action=None, data={})
        self.tried.setdefault(key, set()).add(action)
        certificate = dict(kind='animated_switch_navigation', source=self.t, tag=tag, scene=s,
                           moves=copy.deepcopy(self.moves), transitions=copy.deepcopy(self.transitions),
                           failures=copy.deepcopy(self.failures), cue=self.cue, cue_trials=copy.deepcopy(self.cue_trials),
                           revisions=copy.deepcopy(self.revisions), archive=copy.deepcopy(self.archive),
                           hypothesis=hypothesis, prior_geometry_is_hypothesis=True, transfer_control_priority_is_hypothesis=bool(self.archive))
        self.previous = dict(raw=copy.deepcopy(raw), scene=copy.deepcopy(s), mode=mode)
        self.last = action; self.t += 1
        return dict(done=False, action=action, data={}, certificate=certificate)
