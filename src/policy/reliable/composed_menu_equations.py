"""Bounded inverse composition with explicit domains for intermediate words."""
from collections import deque
from editable_word_programs import solutions as direct_solutions

def solutions(source,target,first_schema,second_schema,output_domains,cap=4096,program_cap=256):
    source,target=tuple(source),tuple(target)
    assert len(first_schema)==len(output_domains)
    domains=[tuple(sorted(set(tuple(v) for v in values if len(v)==m)))
             for (n,m),values in zip(first_schema,output_domains)]
    assert all(n>0 and m>0 for n,m in tuple(first_schema)+tuple(second_schema))
    queue=deque([(0,(None,)*len(first_schema),(),())]);seen=set();found={}
    secondary_expanded=0;secondary_truncated=False
    while queue and len(seen)<cap and len(found)<program_cap:
        at,assigned,middle,path=queue.popleft();key=at,assigned,middle
        if key in seen:continue
        seen.add(key)
        if at==len(source):
            if any(v is None for v in assigned):continue
            right=direct_solutions(middle,target,second_schema,cap=cap)
            secondary_expanded+=right['expanded'];secondary_truncated|=right['overflow']
            for second,derivation in right['programs']:
                pair=assigned,second
                found.setdefault(pair,dict(first=assigned,second=second,intermediate=middle,
                    first_derivation=path,second_derivation=derivation))
                if len(found)>=program_cap:break
            continue
        for k,(n,m) in enumerate(first_schema):
            if at+n>len(source):continue
            left=source[at:at+n]
            if any(v is not None and j!=k and (left[:len(v[0])]==v[0] or v[0][:len(left)]==left)
                   for j,v in enumerate(assigned)):continue
            outputs=(assigned[k][1],) if assigned[k] is not None and assigned[k][0]==left else () if assigned[k] is not None else domains[k]
            for output in outputs:
                rule=left,output;child=list(assigned);child[k]=rule
                queue.append((at+n,tuple(child),middle+output,path+((k,at,at+n,len(middle),len(middle)+m),)))
    return dict(programs=list(found.values()),expanded=len(seen),secondary_expanded=secondary_expanded,
        truncated=bool(queue) or secondary_truncated or len(found)>=program_cap,
        scope='Candidate equations only. Domains must come from independent observations or be explicitly marked teacher constraints. No assertion of reachable controls or correct environment goal.')
