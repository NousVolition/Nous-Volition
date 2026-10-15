"""Conservative sampling bounds for rare capture counts; no model modifications.

For independent, not necessarily identically distributed Bernoulli indicators,
the exponential-moment bound gives P(S<=k) <= exp[-mu+k+k log(mu/k)]
when mu>k, with the corresponding upper-tail bound for mu<k. Invert with
alpha/2 in each tail. Global inlet-weight bounds convert count means to CE.
These bounds cover sampled finite-domain/time outcomes, not physical truth.
"""
import numpy as np
from scipy.optimize import brentq
def count_mean_bounds(k,n,alpha=.05):
    if not 0<=k<=n:raise ValueError('invalid count')
    threshold=-np.log(alpha/2)
    if k==0:return 0.,min(float(n),threshold)
    def f(mu):return mu-k-k*np.log(mu/k)-threshold
    low=brentq(f,max(1e-300,k*1e-12),float(k))
    high=float(n) if k==n or f(float(n))<=0 else brentq(f,float(k),float(n))
    return low,high

def flux_bounds(k,n,bmax,zmax,ph):
    lo,hi=count_mean_bounds(k,n)
    wlo=max(0.,1-1.5/zmax-abs(ph)/zmax**2)
    whi=1+abs(ph)/zmax**2
    return bmax*bmax*wlo*lo/n,bmax*bmax*whi*hi/n
