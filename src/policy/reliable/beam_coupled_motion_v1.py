"""Infer rigid co-motion components from retained successful movements."""
def infer(evidence,count):
    groups=[{i}for i in range(count)];sources=[]
    for r in evidence:
        if r['action']not in(1,2,3,4)or len(r['before'])!=count:continue
        deltas=[tuple(b-a for a,b in zip(p,q))for p,q in zip(r['before'],r['after'])]
        moved={i for i,d in enumerate(deltas)if d!=(0,0)}
        if len(moved)<2 or len({deltas[i]for i in moved})!=1:continue
        merge=set().union(*(g for g in groups if g&moved));groups=[g for g in groups if not g&moved]+[merge];sources.append(r['source'])
    return sorted(tuple(sorted(g))for g in groups),sources
