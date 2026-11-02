"""Public-observation measurement and prospective, append-only evidence records."""
from collections import Counter, deque
from copy import deepcopy
import hashlib
import gc
import json
from composite_components import append_composites,palette


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def observation(value):
    required = {'frame', 'state', 'available_actions', 'levels_completed'}
    if type(value) is not dict or set(value) != required:
        raise ValueError('Only the four public observation fields are accepted')
    frame = value['frame']
    if type(frame) is not list or not 1 <= len(frame) <= 64:
        raise ValueError('Invalid frame height')
    width = len(frame[0]) if type(frame[0]) is list else 0
    if not 1 <= width <= 64 or any(type(row) is not list or len(row) != width for row in frame):
        raise ValueError('Invalid rectangular frame')
    if any(type(v) is not int or not 0 <= v <= 15 for row in frame for v in row):
        raise ValueError('Invalid symbolic color')
    if value['state'] not in ('NOT_PLAYED', 'NOT_FINISHED', 'WIN', 'GAME_OVER'):
        raise ValueError('Unknown public state')
    acts = value['available_actions']
    if type(acts) is not list or any(type(a) is not int for a in acts) or len(set(acts)) != len(acts):
        raise ValueError('Invalid available actions')
    if type(value['levels_completed']) is not int or value['levels_completed'] < 0:
        raise ValueError('Invalid level count')
    return dict(frame=[row[:] for row in frame],state=value['state'],available_actions=acts[:],levels_completed=value['levels_completed'])


def _compute_primitives(frame):
    height, width = len(frame), len(frame[0])
    seen, out = set(), []
    for r in range(height):
        for c in range(width):
            if (r, c) in seen:
                continue
            label = frame[r][c]
            queue, cells = deque([(r, c)]), []
            seen.add((r, c))
            while queue:
                y, x = queue.popleft()
                cells.append((y, x))
                for ny, nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                    if 0 <= ny < height and 0 <= nx < width and (ny,nx) not in seen and frame[ny][nx] == label:
                        seen.add((ny,nx)); queue.append((ny,nx))
            cells.sort()
            top, left = min(y for y,x in cells), min(x for y,x in cells)
            shape = tuple((y-top,x-left) for y,x in cells)
            out.append(dict(label=label, origin_rc=[top,left], shape_rc=[list(p) for p in shape],
                            cells_rc=[list(p) for p in cells], size=len(cells)))
    return out


def _compute_components(frame):
    return append_composites(frame,primitive_components(frame))



# Cached values are immutable; every caller receives newly allocated lists.
# Cache keys contain only the actual frame supplied to perception.
from functools import lru_cache
from itertools import chain
import numpy as np

def _freeze_parts(parts):
    return tuple((p['label'],tuple(p['origin_rc']),bytes(chain.from_iterable(p['shape_rc'])),
                  bytes(chain.from_iterable(p['cells_rc'])),p['size'],
                  tuple(p['palette']) if 'palette' in p else None,p.get('interpretation')) for p in parts)

def _thaw_parts(parts):
    enabled=gc.isenabled()
    if enabled:gc.disable()
    try:
        out=[]
        for label,origin,shape,cells,size,palette_,interpretation in parts:
            p=dict(label=label,origin_rc=list(origin),shape_rc=np.frombuffer(shape,dtype=np.uint8).reshape(-1,2).tolist(),cells_rc=np.frombuffer(cells,dtype=np.uint8).reshape(-1,2).tolist(),size=size)
            if palette_ is not None:p['palette']=list(palette_)
            if interpretation is not None:p['interpretation']=interpretation
            out.append(p)
        return out
    finally:
        if enabled:gc.enable()

@lru_cache(maxsize=16)
def _cached_primitives(frame):return _freeze_parts(_compute_primitives(frame))

@lru_cache(maxsize=16)
def _cached_components(frame):return _freeze_parts(_compute_components(frame))

def primitive_components(frame):
    return _thaw_parts(_cached_primitives(tuple(tuple(row) for row in frame)))

def components(frame):
    return _thaw_parts(_cached_components(tuple(tuple(row) for row in frame)))

def measure(before, after):
    before, after = observation(before), observation(after)
    a, b = before['frame'], after['frame']
    boundary = before['levels_completed'] != after['levels_completed'] or after['state'] != 'NOT_FINISHED'
    if (len(a),len(a[0])) != (len(b),len(b[0])):
        return dict(comparable=False, reason='shape_changed', boundary=boundary, motions=[])
    changes = [[r,c,a[r][c],b[r][c]] for r in range(len(a)) for c in range(len(a[0])) if a[r][c] != b[r][c]]
    counts_a, counts_b = Counter(v for row in a for v in row), Counter(v for row in b for v in row)
    groups = []
    for frame in (a,b):
        by_signature = {}
        for comp in components(frame):
            key = (comp['label'], tuple(tuple(p) for p in comp['shape_rc']))
            by_signature.setdefault(key, []).append(comp)
        groups.append(by_signature)
    motions = []
    if not boundary:
        for key, first in groups[0].items():
            second = groups[1].get(key, [])
            if len(first) == len(second) == 1:
                p, q = first[0], second[0]
                delta = [q['origin_rc'][i]-p['origin_rc'][i] for i in (0,1)]
                if delta != [0,0]:
                    motions.append(dict(label=p['label'], shape_rc=p['shape_rc'], before_rc=p['origin_rc'],
                                        after_rc=q['origin_rc'], delta_rc=delta, size=p['size'],
                                        interpretation='appearance_correspondence_not_identity_proof'))
    return dict(comparable=True, boundary=boundary, frames_equal=not changes, changed_cells=len(changes),
                counts_equal=counts_a == counts_b, changes=changes, motions=motions)


class EvidenceLedger:
    """One pending physical action; its prior observation and prediction are immutable."""
    def __init__(self):
        self._rows, self._pending = [], None

    @property
    def rows(self):
        return deepcopy(self._rows)

    def _append(self, kind, payload):
        row = dict(sequence=len(self._rows), kind=kind, payload=deepcopy(payload),
                   previous=self._rows[-1]['hash'] if self._rows else None)
        row['hash'] = digest(row)
        self._rows.append(row)
        return row['hash']

    def predict(self, before, action, prediction=None):
        if self._pending is not None:
            raise RuntimeError('Previous action has no measured result')
        obs = observation(before)
        if type(action) is not int or action not in obs['available_actions'] or obs['state'] != 'NOT_FINISHED':
            raise ValueError('Action is not currently legal')
        if prediction is not None:
            if type(prediction) is not dict or set(prediction) != {'label','shape_rc','delta_rc'} or type(prediction['label']) is not int:
                raise ValueError('Invalid displacement prediction')
            palette(prediction['label'])  # Feature IDs never alter the raw0..15 frame alphabet.
            shape = prediction['shape_rc']
            if type(shape) is not list or not shape or any(type(p) is not list or len(p) != 2 or any(type(v) is not int or not 0 <= v < 64 for v in p) for p in shape):
                raise ValueError('Invalid predicted appearance shape')
            delta = prediction['delta_rc']
            if type(delta) is not list or len(delta) != 2 or any(type(n) is not int for n in delta):
                raise ValueError('Invalid displacement')
        self._pending = dict(before=obs, action=action, prediction=deepcopy(prediction))
        return self._append('prediction', dict(before_sha256=digest(obs), action=action, prediction=prediction))

    def observe(self, after):
        if self._pending is None:
            raise RuntimeError('Observation needs a recorded prior action')
        after = observation(after)
        pending = self._pending
        measured = measure(pending['before'], after)
        prediction, status, actual = pending['prediction'], 'unpredicted', None
        if prediction is not None:
            status = 'unknown'
            if measured['comparable'] and not measured['boundary']:
                match = [m for m in measured['motions'] if m['label'] == prediction['label'] and m['shape_rc'] == prediction['shape_rc']]
                before_c = [c for c in components(pending['before']['frame']) if c['label'] == prediction['label'] and c['shape_rc'] == prediction['shape_rc']]
                after_c = [c for c in components(after['frame']) if c['label'] == prediction['label'] and c['shape_rc'] == prediction['shape_rc']]
                if len(match) == 1:
                    actual = match[0]['delta_rc']
                elif len(before_c) == len(after_c) == 1 and before_c[0]['cells_rc'] == after_c[0]['cells_rc']:
                    actual = [0,0]
                if actual is not None:
                    status = 'consistent' if actual == prediction['delta_rc'] else 'refuted'
        result = dict(action=pending['action'], before_sha256=digest(pending['before']), after_sha256=digest(after),
                      measurement=measured, prediction_status=status, observed_delta_rc=actual)
        result['evidence_hash'] = self._append('observation', result)
        self._pending = None
        return deepcopy(result)

    def observation_record(self, evidence_hash):
        self.verify()
        found = [row for row in self._rows if row['hash'] == evidence_hash and row['kind'] == 'observation']
        if len(found) != 1:
            raise ValueError('Measured evidence is absent from this ledger')
        return dict(deepcopy(found[0]['payload']), evidence_hash=evidence_hash)

    def verify(self):
        previous = None
        for i, saved in enumerate(self._rows):
            row = saved.copy(); expected = row.pop('hash')
            if row['sequence'] != i or row['previous'] != previous or digest(row) != expected:
                raise ValueError('Evidence chain differs')
            previous = expected
        return self._pending is None
