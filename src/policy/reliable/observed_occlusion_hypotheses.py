"""Tentative continuations of an observed shape behind visible foreground pixels."""
from collections import Counter
import numpy as np
from scipy.ndimage import label
from scipy.signal import correlate2d

def candidates(frame, template):
    color, shape, _ = template
    a = np.asarray(frame)
    height = max(y for y, x in shape) + 1
    width = max(x for y, x in shape) + 1
    mask = np.zeros((height, width), dtype=np.int32)
    for y, x in shape:
        mask[y, x] = 1
    visible = (a == color).astype(np.int32)
    visible_count = int(visible.sum())
    area = len(shape)
    if not area // 2 <= visible_count < area:
        return []
    background = int(np.bincount(a.ravel()).argmax())
    if color == background:
        return []
    visible_overlap = correlate2d(visible, mask, mode="valid")
    background_overlap = correlate2d((a == background).astype(np.int32), mask, mode="valid")
    positions = np.argwhere((visible_overlap == visible_count) & (background_overlap == 0))
    out = []
    labels = {}
    for y, x in positions:
        y, x = int(y), int(x)
        body = {(y + dy, x + dx) for dy, dx in shape}
        missing = sorted((u, v) for u, v in body if a[u, v] != color)
        by_color = Counter(int(a[u, v]) for u, v in missing)
        crossing = []
        enclosed = []
        valid = True
        for other in sorted(by_color):
            if other not in labels:
                labels[other] = label(a == other)[0]
            lab = labels[other]
            ids = {int(lab[u, v]) for u, v in missing if a[u, v] == other}
            for component in ids:
                points = {tuple(map(int, p)) for p in np.argwhere(lab == component)}
                inside = points & body
                if points - body:
                    crossing.append(dict(color=other, inside=sorted(inside), outside_pixels=len(points - body)))
                else:
                    # Small enclosed markings already supported by the preceding
                    # completion mechanism may coexist with a larger occluder.
                    if len(points) != 1:
                        valid = False
                        break
                    u, v = next(iter(points))
                    if not all((u + dy, v + dx) in body for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        valid = False
                        break
                    enclosed.append((u, v))
            if not valid:
                break
        if valid and crossing and len(enclosed) <= max(1, area // 8):
            out.append(dict(pose=(int(color), shape, (y, x)), visible_pixels=visible_count,
                missing_pixels=missing, crossing_occluders=crossing, enclosed_markings=enclosed,
                scope="An earlier observed shape can contain all current pixels of its color, with at least half still visible. Missing pixels are visible foreground components extending outside that shape or isolated interior markings. This is a continuity hypothesis, not hidden-state truth."))
    return out
