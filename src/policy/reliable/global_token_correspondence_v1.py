"""Fit a tentative unrestricted bijection from actual color correspondences.

Spatial proximity and minimum movement are priors,not supplied control laws.
Every predicted successor is rechecked against actual outcomes by the learner.
"""
import numpy as np
from scipy.optimize import linear_sum_assignment

def constraints(cells,before,after,old=None):
    n=len(cells);dist=[[((a[0]-b[0])**2+(a[1]-b[1])**2) for b in cells] for a in cells]
    radius=max(v for row in dist for v in row)
    allowed=tuple(tuple(dist[i][j]<=radius and before[j]==after[i] and (old is None or old[i][j]) for j in range(n)) for i in range(n))
    cost=np.asarray([[dist[i][j] if allowed[i][j] else 10**9 for j in range(n)] for i in range(n)],dtype=np.int64)
    rows,columns=linear_sum_assignment(cost)
    if any(not allowed[i][j] for i,j in zip(rows,columns)):return allowed,None,radius
    permutation=[0]*n
    for i,j in zip(rows,columns):permutation[int(i)]=int(j)
    return allowed,tuple(permutation),radius
