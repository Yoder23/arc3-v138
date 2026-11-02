"""Apply witnessed body barriers while testing unconfirmed delivery surfaces."""
from collections import deque
from carry_material_transfer_v3 import Controller as Base
from observed_transport_memory_v1 import add, feature


class Controller(Base):
    def respond(self, raw):
        self._material_frame = raw['frame']
        return super().respond(raw)

    def route(self, v, target, offset=None):
        barriers = {look for look, _ in self.transport.barriers(self.level)}
        if not barriers or self.transport_active():
            return super().route(v, target, offset)
        start = tuple(v['body']['box'][:2]); target = tuple(target); n = v['n']
        cargo = self.positions(v)
        loose = cargo - ({add(start, offset)} if offset is not None else set())
        frame = self._material_frame
        # A failed empty-hand move into the box is not a carrying failure.
        failed = {(r['pose'], r['action']) for r in self.carry_failures.values()
                  if r['level'] == self.level and r['grasp'] == offset
                  and set(r['cargo']) - {add(r['pose'], offset)} == loose} if offset is not None else {
                      (p, a) for p, a, c in self.blocked if set(c) == cargo}
        todo = deque([start]); previous = {start: None}
        while todo:
            p = todo.popleft()
            if p == target:
                break
            for action, motion in sorted(self.motions.items()):
                q = add(p, motion['delta'])
                if q in previous or q in loose or not all(0 <= k <= 64-n for k in q):
                    continue
                if feature(frame, q, n) in barriers or (p, action) in failed:
                    continue
                if (self.level, p, action) in getattr(self, 'blind_entries', set()):
                    continue
                if offset is not None:
                    held = add(q, offset)
                    if held in loose or not all(0 <= k <= 64-n for k in held):
                        continue
                previous[q] = (p, action); todo.append(q)
        if target not in previous:
            return None
        path = []; p = target
        while previous[p] is not None:
            p, action = previous[p]; path.append(action)
        return path[::-1]

    def material_action(self, raw, v, action, tag):
        response = super().material_action(raw, v, action, tag)
        # Let the existing failure learner retain the actual grasp context.
        self.previous['experiment_grasp'] = self.held
        return response
