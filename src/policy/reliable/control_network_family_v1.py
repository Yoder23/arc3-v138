"""Palette-independent connected-control geometry, used as a transfer hypothesis."""
from binary_demonstration_bootstrap_v1 import components


def family(frame,scene,position):
    n=scene['actor']['box'][2];cy,cx=position[0]+n//2,position[1]+n//2
    candidates=[o for o in components(frame)if o['box'][0]<=cy<o['box'][0]+o['box'][2]
                and o['box'][1]<=cx<o['box'][1]+o['box'][3]
                and(cy-o['box'][0],cx-o['box'][1])in o['shape']]
    if len(candidates)!=1:return 'unknown'
    o=candidates[0];points=set(o['shape']);h,w=o['box'][2:]
    solid=any(all((y+dy,x+dx)in points for dy in range(n)for dx in range(n))
              for y in range(h-n+1)for x in range(w-n+1))
    return 'network_with_solid_body' if solid else 'network_without_solid_body'
