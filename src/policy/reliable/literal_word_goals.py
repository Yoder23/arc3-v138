"""Tentative words from token fills or their uniform surrounding outlines."""
from collections import Counter
from literal_word_rows import values


def channels(frame, row):
    result = {}
    fill = values(frame, row)
    if fill is not None:
        result["fill"] = fill
    h, w = len(frame), len(frame[0])
    populations = Counter(v for r in frame for v in r)
    background = min(populations, key=lambda c: (-populations[c], c))
    for thickness in (1, 2):
        word = []
        for y, x, dy, dx in row:
            top, left = y - thickness, x - thickness
            bottom, right = y + dy - 1 + thickness, x + dx - 1 + thickness
            if not (0 <= top <= bottom < h and 0 <= left <= right < w):
                break
            ring = {frame[v][u] for v in range(top, bottom + 1) for u in range(left, right + 1)
                    if v in (top, bottom) or u in (left, right)}
            if len(ring) != 1:
                break
            word.append(next(iter(ring)))
        if len(word) == len(row) and background not in word:
            result[f"outline{thickness}"] = tuple(word)
    return result
