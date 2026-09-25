"""Label-free NuSTAR measurement pilot for the locked positive continuum.

No classifier, source table, class field, or mission-transfer machinery is used.
All spectral fits are gated by the completed X1 measurement audit.
"""
from pathlib import Path
import json, numpy as np
from astropy.io import fits
from scipy.sparse import csr_matrix
from scipy.optimize import minimize, LinearConstraint
from scipy.special import xlogy

NODES=np.array([5.,8.,12.,18.,25.])
BANDS=list(zip(NODES[:-1],NODES[1:]))
KEV_ERG=1.602176634e-9

def basis(energy):
    """Log-linear interpolation, tied outer guards and slope extrapolation."""
    x=np.log(np.asarray(energy));k=np.clip(np.searchsorted(np.log(NODES),x)-1,0,3)
    t=(x-np.log(NODES[k]))/np.log(NODES[k+1]/NODES[k])
    b=np.zeros((x.size,5));b[np.arange(x.size),k]=1-t;b[np.arange(x.size),k+1]=t
    return b

def integration(lo,hi,order=8):
    # Explicitly split bins at continuum knots before Gaussian quadrature.
    xs,ws,owners=[],[],[];z,w=np.polynomial.legendre.leggauss(order)
    for i,(a,b) in enumerate(zip(lo,hi)):
        cuts=np.r_[a,NODES[(NODES>a)&(NODES<b)],b]
        for left,right in zip(cuts[:-1],cuts[1:]):
            xs.extend((left+right)/2+(right-left)/2*z);ws.extend(w*(right-left)/2);owners.extend([i]*order)
    return np.array(xs),np.array(ws),np.array(owners)

def profile_background(source,background,model,alpha):
    a=alpha*(1+alpha);c=(1+alpha)*model-alpha*(source+background)
    d=np.sqrt(c*c+4*a*background*model)
    return np.where(c>=0,2*background*model/np.maximum(d+c,1e-300),(-c+d)/(2*a))

def poisson_deviance(observed,expected):
    return 2*np.sum(expected-observed+xlogy(observed,observed/np.maximum(expected,1e-300)))

def group_channels(background,energy,min_background=5):
    """Contiguous source+background bins, never crossing declared band edges.

    Sparse-background W-stat bias is audited with 1/5/10-count variants;
    grouping changes the likelihood resolution, never the physical bands.
    """
    groups=[]
    for lo,hi in BANDS:
        ids=np.flatnonzero((energy>=lo)&(energy<hi));chunk=[];count=0;band=[]
        for i in ids:
            chunk.append(i);count+=background[i]
            if count>=min_background:band.append(chunk);chunk=[];count=0
        if chunk:
            if band:band[-1].extend(chunk)
            else:band.append(chunk)
        groups.extend(band)
    row=[];col=[]
    for i,ids in enumerate(groups):row.extend([i]*len(ids));col.extend(ids)
    return csr_matrix((np.ones(len(row)),(row,col)),shape=(len(groups),len(background)))

class Measurement:
    def __init__(self,paths,min_background=5,area_scale=1.,area_tilt=0.,guard_limits=None):
        # Explicit allowlist makes labels and identity metadata invalid inputs.
        if set(paths)!={'source','background','arf','rmf'}:raise ValueError('Only four spectral product paths are accepted')
        with fits.open(paths['source']) as h:
            s=h['SPECTRUM'];source=s.data['COUNTS'].astype(float);self.exposure=float(s.header['EXPOSURE']);bs=float(s.header['BACKSCAL']);asc=float(s.header['AREASCAL'])
            if not s.header.get('POISSERR',False):raise ValueError('NuSTAR Poisson source required')
            quality=s.data['QUALITY'] if 'QUALITY' in s.columns.names else np.zeros(len(source))
        with fits.open(paths['background']) as h:
            b=h['SPECTRUM'];background=b.data['COUNTS'].astype(float)
            self.alpha=self.exposure/b.header['EXPOSURE']*bs/b.header['BACKSCAL']
            if not b.header.get('POISSERR',False):raise ValueError('Independent Poisson off-source data required')
            if float(b.header['AREASCAL'])!=1 or asc!=1:raise ValueError('Nonunit AREASCAL needs explicit implementation')
        with fits.open(paths['arf']) as h:area=h['SPECRESP'].data['SPECRESP'].astype(float)
        with fits.open(paths['rmf']) as h:
            e=h['EBOUNDS'].data;m=h['MATRIX'].data
            mask=(e['E_MIN']>=5-1e-5)&(e['E_MAX']<=25+1e-5)&(quality==0)
            self.energy=((e['E_MIN']+e['E_MAX'])/2)[mask].astype(float)
            self.lo=m['ENERG_LO'].astype(float);self.hi=m['ENERG_HI'].astype(float)
            rows=[];cols=[];values=[];offset=int(e['CHANNEL'][0])
            for j,r in enumerate(m):
                n=0
                for start,width in zip(np.atleast_1d(r['F_CHAN'])[:r['N_GRP']],np.atleast_1d(r['N_CHAN'])[:r['N_GRP']]):
                    start=int(start)-offset;width=int(width);rows.extend(range(start,start+width));cols.extend([j]*width);values.extend(r['MATRIX'][n:n+width]);n+=width
            response=csr_matrix((values,(rows,cols)),shape=(len(e),len(m)))[mask]
        self.raw_source=source[mask];self.raw_background=background[mask]
        self.group=group_channels(self.raw_background,self.energy,min_background)
        self.source=np.asarray(self.group@self.raw_source).ravel();self.background=np.asarray(self.group@self.raw_background).ravel()
        mid=np.sqrt(self.lo*self.hi);area=area*area_scale*(mid/np.sqrt(5*25))**area_tilt
        self.response=self.exposure*self.group@response.multiply(area)
        self.qe,self.qw,self.qid=integration(self.lo,self.hi,order=4)
        if guard_limits is not None:self.qw*=((self.qe>=guard_limits[0])&(self.qe<=guard_limits[1]))
        self.qb=basis(self.qe)
        self.fe,self.fw,self.fid=integration(NODES[:-1],NODES[1:],order=32);self.fb=basis(self.fe)
        slope=np.diff(np.eye(5),axis=0)/np.diff(np.log(NODES))[:,None]
        self.constraint=LinearConstraint(np.vstack([slope,basis([3.,40.])]),np.r_[np.full(4,-6.),np.full(2,np.log(1e-12))],np.r_[np.full(4,2.),np.full(2,np.log(1e3))])

    def expected(self,theta):
        weighted=np.exp(self.qb@theta)*self.qw
        incident=np.bincount(self.qid,weights=weighted,minlength=len(self.lo))
        derivative=np.column_stack([np.bincount(self.qid,weights=weighted*self.qb[:,i],minlength=len(self.lo)) for i in range(5)])
        return np.asarray(self.response@incident).ravel(),np.asarray(self.response@derivative)

    def objective(self,theta):
        model,jac=self.expected(theta);b=profile_background(self.source,self.background,model,self.alpha);mu=model+self.alpha*b
        nll=(poisson_deviance(self.source,mu)+poisson_deviance(self.background,b))/2
        gradient=jac.T@(1-self.source/np.maximum(mu,1e-300))
        return nll,gradient

    def fit(self,start=None):
        trials=[]
        slopes=[2.,1.,3.] if start is None else [None]
        for slope in slopes:
            if start is None:
                x=-slope*np.log(NODES/8)-5
                model,_=self.expected(x);x+=np.log(max((self.source-self.alpha*self.background).sum(),1)/model.sum())
            else:x=np.array(start)
            r=minimize(self.objective,x,jac=True,method='SLSQP',bounds=[(np.log(1e-12),np.log(1e3))]*5,constraints=[self.constraint],options={'maxiter':500,'ftol':1e-9})
            vals=self.constraint.A@r.x
            valid=np.all(vals>=self.constraint.lb-1e-6) and np.all(vals<=self.constraint.ub+1e-6)
            if r.success and valid:trials.append(r)
        if not trials:raise ValueError('Continuum optimization failed')
        r=min(trials,key=lambda v:v.fun);theta=r.x
        h=1e-4;hess=np.column_stack([(self.objective(theta+np.eye(5)[i]*h)[1]-self.objective(theta-np.eye(5)[i]*h)[1])/(2*h) for i in range(5)]);hess=(hess+hess.T)/2
        eig=np.linalg.eigvalsh(hess)
        if eig.min()<=0:raise ValueError('Nonpositive information matrix')
        covariance=np.linalg.inv(hess);flux,jac=self.flux(theta);fluxcov=jac@covariance@jac.T
        slopes=-np.diff(theta)/np.diff(np.log(NODES));contact=bool(np.any(slopes<-2+1e-4)|np.any(slopes>6-1e-4)|np.any(theta<np.log(1e-12)+1e-4)|np.any(theta>np.log(1e3)-1e-4))
        model,_=self.expected(theta);b=profile_background(self.source,self.background,model,self.alpha)
        return dict(theta=theta,covariance=covariance,flux=flux,flux_covariance=fluxcov,flux_sigma=np.sqrt(np.diag(fluxcov)),deviance=2*r.fun,groups=len(self.source),nominal_dof=len(self.source)-5,photon_indices=slopes,bound_contact=contact,optimizer_message=r.message,model_counts=model,profile_background=b,source_counts=self.source,background_counts=self.background,alpha=self.alpha,hessian_min_eigenvalue=float(eig.min()))

    def flux(self,theta):
        v=np.exp(self.fb@theta)*self.fw*self.fe*KEV_ERG
        return np.bincount(self.fid,weights=v,minlength=4),np.column_stack([np.bincount(self.fid,weights=v*self.fb[:,i],minlength=4) for i in range(5)])

def features(flux,covariance):
    f=np.asarray(flux,float);c=np.asarray(covariance,float)
    if f.shape!=(4,) or c.shape!=(4,4) or not np.isfinite(f).all() or (f<=0).any():raise ValueError('Four positive physical fluxes and covariance required')
    t=f.sum();a=np.log10(f);b=f/t;cv=np.array([np.log10(f[1]/f[0]),np.log10(f[3]/f[2]),np.log10(t)])
    ja=np.diag(1/(np.log(10)*f));jb=np.eye(4)/t-f[:,None]/t**2
    jc=np.array([[-1/f[0],1/f[1],0,0],[0,0,-1/f[2],1/f[3]],np.ones(4)/t])/np.log(10)
    return {name:dict(values=val,covariance=jac@c@jac.T,sigma=np.sqrt(np.maximum(np.diag(jac@c@jac.T),0))) for name,val,jac in [('A',a,ja),('B',b,jb),('C',cv,jc)]}

def serialize(x):
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,np.generic):return x.item()
    raise TypeError(type(x).__name__)
