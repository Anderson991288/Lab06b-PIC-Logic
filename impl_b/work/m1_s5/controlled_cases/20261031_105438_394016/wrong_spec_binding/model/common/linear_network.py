"""Shared embedding, propagation order and fixed power-difference readout."""
import numpy as np
from .mzi import apply_matrix,powers


def _index(value,n,name):
    if not isinstance(value,(int,np.integer)) or isinstance(value,bool) or not 0<=value<n:
        raise ValueError(name+' is outside the port range')
    return int(value)


def embed_2x2(matrix,i,j,n_modes):
    if not isinstance(n_modes,(int,np.integer)) or isinstance(n_modes,bool) or n_modes<2:raise ValueError('n_modes must be integer >=2')
    i=_index(i,n_modes,'i');j=_index(j,n_modes,'j')
    matrix=np.asarray(matrix,dtype=complex)
    if i==j or matrix.shape!=(2,2) or not np.isfinite(matrix).all():raise ValueError('Use distinct ports and a finite 2x2 matrix')
    result=np.eye(n_modes,dtype=complex);result[np.ix_([i,j],[i,j])]=matrix
    return result


def cascade(stages,n_modes):
    """stages are listed in the physical order encountered by light."""
    if not isinstance(n_modes,(int,np.integer)) or isinstance(n_modes,bool) or n_modes<1:raise ValueError('n_modes must be positive integer')
    total=np.eye(n_modes,dtype=complex)
    for stage in stages:
        stage=np.asarray(stage,dtype=complex)
        if stage.shape!=(n_modes,n_modes) or not np.isfinite(stage).all():raise ValueError('Every stage must match n_modes')
        total=stage@total
    return total


def propagate_stages(stages,input_field):
    field=np.asarray(input_field,dtype=complex).copy()
    if field.ndim!=1 or not np.isfinite(field).all():raise ValueError('Expected finite 1-D input')
    rows=[field.copy()]
    for stage in stages:
        field=apply_matrix(stage,field);rows.append(field.copy())
    return rows


def power_difference_readout(field,positive=1,negative=3,threshold=0.,epsilon=1e-10):
    p=powers(field)
    positive=_index(positive,len(p),'positive');negative=_index(negative,len(p),'negative')
    if positive==negative:raise ValueError('Readout ports must be distinct')
    threshold=float(threshold);epsilon=float(epsilon)
    if not np.isfinite(threshold) or not np.isfinite(epsilon) or epsilon<0:raise ValueError('Invalid threshold or epsilon')
    delta=float(p[positive]-p[negative]);margin=delta-threshold
    bit=None if abs(margin)<=epsilon else int(margin>0)
    return {'positive_power':float(p[positive]),'negative_power':float(p[negative]),
            'delta':delta,'margin':margin,'bit':bit,'boundary':bit is None}
