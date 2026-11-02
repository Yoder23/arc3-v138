"""Rebind a moving marker to its currently occupied visible compartment."""
def targets(s,g):
    result=[None]*len(g['segments']);orth=1-g['axis'];bindings=[]
    for p in s['pairs']:
        at=p['actor']['box'][orth]+p['actor']['box'][orth+2]/2
        hits=[i for i,z in enumerate(g['segments'])if z['span'][0]<=at<z['span'][1] and z['bounds'][0]<=p['current']<=z['bounds'][1]]
        prior=next((b for b in g['bindings']if b['ink']==p['ink']),None)
        if len(hits)!=1 or prior is None:return tuple(g['targets'])
        result[hits[0]]=p['target']-prior['offset']
    return tuple(result)
