"""Keep distinct achieved-goal subsets while composing intermediate layouts."""
def select(ranked,signatures,width):
 buckets={}
 for score,state in ranked:buckets.setdefault(signatures[state],[]).append(state)
 selected=[];keys=list(buckets)
 for depth in range(width):
  for key in keys:
   if depth<len(buckets[key]):selected.append(buckets[key][depth])
   if len(selected)>=width:return selected
 return selected
