"""Grounded word-to-word rewriting with bounded, explicitly ambiguous parsing."""
from collections import defaultdict
from panel_hypotheses_v2 import rectangles, digest
from panel_sequence_hypotheses import glyphs
from panel_control_learner import identity


def translations(source, mapping, length, cap=128):
    """Enumerate distinct outputs; abstain if the bounded search is incomplete."""
    states = {(0, ()): ()}
    complete = {}
    for index in range(len(source)):
        for (at, output), derivation in list(states.items()):
            if at != index:
                continue
            for word, target in sorted(mapping.items()):
                end = at + len(word)
                if source[at:end] != word or len(output) + len(target) > length:
                    continue
                key = (end, output + target)
                candidate = derivation + ((at, end, word, target),)
                if key not in states or len(candidate) < len(states[key]):
                    states[key] = candidate
                if len(states) > cap:
                    return [], True
    for (at, output), derivation in states.items():
        if at == len(source) and len(output) == length:
            complete[output] = derivation
    return sorted(complete.items(), key=lambda p: (len(p[1]), p[0])), False


def candidates(obs, remembered=()):
    proof = digest(obs)
    rects = [dict(r, symbols=glyphs(r)) for r in rectangles(obs['frame']) if glyphs(r)]
    def separation(r, q):
        if r['background'] == q['background']:
            return None
        a,b,c,d = r['box']; y,x,Y,X = q['box']
        if a+c == y+Y and c-a == Y-y and (d < x or X < b):
            return ('horizontal', max(x-d-1, b-X-1))
        if b+d == x+X and d-b == X-x and (c < y or Y < a):
            return ('vertical', max(y-c-1, a-Y-1))
        return None
    nearest = {}
    for i,r in enumerate(rects):
        for axis in ('horizontal','vertical'):
            ds = [(s[1],j) for j,q in enumerate(rects) if j != i
                  and (s := separation(r,q)) is not None and s[0] == axis]
            if ds:
                best = min(d for d,j in ds)
                nearest[i,axis] = {j for d,j in ds if d == best}
    groups = defaultdict(list)
    for (i,axis), js in nearest.items():
        r = rects[i]
        for j in sorted(js):
            if i not in nearest.get((j,axis),set()):
                continue
            q = rects[j]
            # Pair words along their long axis. Square one-symbol words fit either.
            if any((v['box'][2]-v['box'][0] > v['box'][3]-v['box'][1]) != (axis=='vertical')
                   for v in (r,q) if len(v['symbols']) > 1):
                continue
            groups[r['background'],q['background'],axis].append(dict(
                source_masks=tuple(g['mask'] for g in r['symbols']),
                target_masks=tuple(g['mask'] for g in q['symbols']),
                source_box=r['box'],target_box=q['box'],observation=proof))
    maps = []
    for (left,right,axis), examples in sorted(groups.items()):
        mapping = defaultdict(set)
        for e in examples:
            mapping[tuple(identity(m) for m in e['source_masks'])].add(
                tuple(identity(m) for m in e['target_masks']))
        if len(mapping) < 3 or any(len(v) != 1 for v in mapping.values()):
            continue
        maps.append(dict(source_background=left,target_background=right,axis=axis,
                         mapping={k:next(iter(v)) for k,v in mapping.items()},examples=examples))
    proposals = []; truncated = 0
    for m in maps if maps else remembered:
        used = {tuple(e[k]) for e in m['examples'] if e['observation']==proof
                for k in ('source_box','target_box')}
        for left in rects:
            if left['background'] != m['source_background'] or len(left['symbols']) < 2 or left['box'] in used:
                continue
            for right in rects:
                if right['background'] != m['target_background'] or right['box'] in used:
                    continue
                a,b,c,d = left['box']; y,x,Y,X = right['box']
                h=c-a+1; w=d-b+1; H=Y-y+1; W=X-x+1
                aligned = ((m['axis']=='horizontal' and w>h and W>H and h==H and abs(b+d-x-X)<=1)
                           or (m['axis']=='vertical' and h>w and H>W and w==W and abs(a+c-y-Y)<=1))
                if not aligned:
                    continue
                source = tuple(identity(g['mask']) for g in left['symbols'])
                outputs, overflow = translations(source,m['mapping'],len(right['symbols']))
                truncated += int(overflow)
                for expected, derivation in outputs:
                    proposals.append(dict(kind='visual_word_rewriting',source_box=left['box'],
                        target_box=right['box'],source_background=m['source_background'],
                        target_background=m['target_background'],expected=expected,
                        actual=tuple(g['mask'] for g in right['symbols']),examples=m['examples'],
                        observation=proof,derivation=derivation,alternatives=len(outputs),
                        scope='Tentative segmentation and concatenation of observed word pairs; '
                        'ambiguity retained, no semantics assumed from the current output.'))
    return dict(rectangles=rects,maps=maps,proposals=proposals,truncated=truncated)
