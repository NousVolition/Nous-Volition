"""Declared contextual-support readouts, separate from unchanged corpus dynamics."""
import numpy as np

def kernel(f,center,width,normalize=True):
    k=np.exp((np.cos(2*np.pi*(f.x-center[0]))+np.cos(2*np.pi*(f.y-center[1]))-2)/(2*np.pi*width)**2)
    return k/k.mean() if normalize else k

def setup(f,distance):
    # Coordinates represent two content alternatives, never two inward people/roles.
    centers={'P':(.5,.5),'F':(.5-distance,.5)}
    weights={key:kernel(f,c,.08) for key,c in centers.items()}
    z,_=f.initial(texture=0.,speed=.1)
    S=.3+.12*kernel(f,centers['F'],.10,normalize=False)
    z[2]=f.fft(S)*f.mask
    return z,weights

def readout(f,z,A,weights):
    dz,ph,u,gu,force=f.terms(z,A)
    S=f.real(z[2]);dS=f.real(dz[2]);out={}
    for key,w in weights.items():
        out['c_'+key]=float(np.mean(w*S))
        out['dc_'+key]=float(np.mean(w*dS))
        out['v_'+key]=[float(np.mean(w*u[k])) for k in range(2)]
    out['contrast']=out['c_P']-out['c_F']
    out['contrast_rate']=out['dc_P']-out['dc_F']
    return out

def compatible(r):
    return r['c_P']>1e-6 and r['c_F']>1e-6 and r['contrast_rate']>1e-6

def form_record(**values):
    """Preserve observed descriptors without creating material labels from fields."""
    fields=['perceived_balance','calm','disturbance','recalled_content','retrieval_clarity',
            'event_age','felt_temporal_distance','unspoken_assumption','endorsement',
            'specified_small_change','observed_consequence']
    return {k:values.get(k,None) for k in fields}
