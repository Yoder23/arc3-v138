"""Bounded acquisition of unexplained patches on an observed miniature lattice."""
import copy
import numpy as np
from partial_nested_perception import expanded


def hypotheses(frame, memory):
    a = np.asarray(frame)
    found = {}
    for scene in expanded(frame, memory):
        size = scene['size']; sy, sx = scene['pitch']; n = size // 3
        oy, ox = scene['cells'][0][0] % sy, scene['cells'][0][1] % sx
        palette = {v for y, x, v in scene['cells']}
        palette |= {m['pattern'][1][1] for m in scene['markers']}
        uniform = {}
        for y in range(oy, len(a)-size+1, sy):
            for x in range(ox, a.shape[1]-size+1, sx):
                q = a[y:y+size, x:x+size]
                if np.all(q == q[0, 0]) and int(q[0, 0]) in palette:
                    uniform[y, x] = int(q[0, 0])
        for y in range(oy, len(a)-size+1, sy):
            for x in range(ox, a.shape[1]-size+1, sx):
                q = a[y:y+size, x:x+size]
                if np.all(q == q[0, 0]):
                    continue
                blocks = [[q[i*n:(i+1)*n, j*n:(j+1)*n] for j in range(3)] for i in range(3)]
                if not all(np.all(b == b[0, 0]) for row in blocks for b in row):
                    continue
                pattern = [[int(b[0, 0]) for b in row] for row in blocks]
                colors = {v for row in pattern for v in row}
                outside = [pattern[i][j] for i in range(3) for j in range(3) if (i,j)!=(1,1)]
                neighbors = [(yy,xx,uniform[yy,xx]) for dy in (-1,0,1) for dx in (-1,0,1)
                    if (dy or dx) and (yy:=y+dy*sy,xx:=x+dx*sx) in uniform]
                if len(colors)>3 or scene['background'] in colors or not colors & palette:
                    continue
                if sum(v not in scene['inks'] for v in outside)<6 or len(neighbors)<2:
                    continue
                found.setdefault((y,x,size), dict(kind='unknown_lattice_probe', action=6,
                    data=dict(x=x+size//2,y=y+size//2), box=(y,x,size,size), pattern=pattern,
                    pitch=(sy,sx), neighbors=neighbors, palette=sorted(palette),
                    interpreted_inks=scene['inks'], background=scene['background'],
                    source=scene['memory']['source'], examples=copy.deepcopy(scene['memory']['examples']),
                    rule=scene['memory']['rule'],
                    scope='Uninterpreted visible patch; one acquisition click. No asserted effect or goal.'))
    return [found[k] for k in sorted(found)]


class Inquiry:
    def __init__(self):
        self.tested = set()
        self.level = None
        self.started = False
        self.events = []
        self.pending = None

    def observe(self, obs):
        if self.pending is not None:
            before, certificate = self.pending
            changed = [(y,x,before['frame'][y][x],v) for y,row in enumerate(obs['frame'])
                for x,v in enumerate(row) if before['frame'][y][x] != v]
            self.events.append(dict(certificate=certificate, changes=changed,
                before_level=before['levels_completed'], after_level=obs['levels_completed'],
                before_state=before['state'], after_state=obs['state']))
            self.pending = None

    def propose(self, obs, memory):
        if obs['state']!='NOT_FINISHED' or 6 not in obs['available_actions']:
            return None
        if self.started and obs['levels_completed'] != self.level:
            return None
        for c in hypotheses(obs['frame'], memory):
            key = tuple(c['box'])
            if key not in self.tested and len(self.tested)<4:
                self.started = True; self.level = obs['levels_completed']; self.tested.add(key)
                self.pending = (copy.deepcopy(obs), copy.deepcopy(c))
                return c
        return None
