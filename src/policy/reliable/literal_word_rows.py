"""Color-token rows and columns, without assigning tool, input or goal roles."""
from collections import defaultdict
from visual_transform_learner import parts


def layouts(frame):
    rectangles = []
    for color, shape, (y, x) in parts(frame):
        h = max(dy for dy, dx in shape) + 1
        w = max(dx for dy, dx in shape) + 1
        if 2 <= min(h, w) and max(h, w) <= 12 and len(shape) == h * w:
            rectangles.append((y, x, h, w))
    result = set()
    for axis in (0, 1):
        groups = defaultdict(set)
        for y, x, h, w in rectangles:
            groups[(x if axis == 0 else y, h, w)].add(y if axis == 0 else x)
        for (fixed, h, w), positions in sorted(groups.items()):
            size = h if axis == 0 else w
            for step in sorted({b - a for a in positions for b in positions if b - a > size}):
                for start in sorted(positions):
                    if start - step in positions:
                        continue
                    run = []
                    pos = start
                    while pos in positions:
                        run.append((pos, fixed, h, w) if axis == 0 else (fixed, pos, h, w))
                        pos += step
                    if 3 <= len(run) <= 8:
                        result.add(tuple(run))
    # Do not keep a regularly subsampled part of a larger detected word.
    return tuple(sorted(r for r in result if not any(set(r) < set(q) for q in result)))


def values(frame, row):
    out = []
    for y, x, h, w in row:
        pixels = {frame[v][u] for v in range(y, y + h) for u in range(x, x + w)}
        if len(pixels) != 1:
            return None
        out.append(next(iter(pixels)))
    return tuple(out)


def center(box):
    y, x, h, w = box
    return (x + (w - 1) // 2, y + (h - 1) // 2)


def contains(box, point):
    y, x, h, w = box
    return x <= point[0] < x + w and y <= point[1] < y + h
