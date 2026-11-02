"""Shared, forward-only MZI model. All vectors are ordered [upper, lower].

Light encounters phi on the upper input, coupler 1, theta on the upper arm,
and coupler 2: T = a C2 P(theta) C1 P(phi). Phases are radians.
This is a lumped model, with optional uniform insertion loss and lossless
coupler imbalance. Geometry, reflections, dispersion and heaters are excluded.
"""
import numpy as np

PORT_ORDER=('upper','lower')
H=np.array([[1,1j],[1j,1]],dtype=complex)/np.sqrt(2)
H.setflags(write=False)


def _real(value,name):
    value=float(value)
    if not np.isfinite(value):raise ValueError(name+' must be finite')
    return value


def coupler(eps=0.):
    """Reciprocal lossless coupler: bar power=0.5+eps, cross=0.5-eps."""
    eps=_real(eps,'eps')
    if not -.5<=eps<=.5:raise ValueError('eps must be within [-0.5, 0.5]')
    c,s=np.sqrt(.5+eps),np.sqrt(.5-eps)
    return np.array([[c,1j*s],[1j*s,c]],dtype=complex)


def phase_shift(phase,arm='upper'):
    phase=_real(phase,'phase')
    if arm not in PORT_ORDER:raise ValueError('arm must be upper or lower')
    return np.diag([np.exp(1j*phase),1.] if arm=='upper' else [1.,np.exp(1j*phase)])


def amplitude_factor(loss_db):
    loss_db=_real(loss_db,'loss_db')
    if loss_db<0:raise ValueError('Passive-model loss_db must be nonnegative')
    return 10.**(-loss_db/20.)


def transfer_matrix(theta,phi=0.,loss_db=0.,mmi_errors=(0.,0.)):
    if len(mmi_errors)!=2:raise ValueError('Provide one imbalance for each coupler')
    return amplitude_factor(loss_db)*(coupler(mmi_errors[1])@phase_shift(theta)@coupler(mmi_errors[0])@phase_shift(phi))


T2=transfer_matrix


def apply_matrix(matrix,input_field):
    matrix=np.asarray(matrix,dtype=complex)
    field=np.asarray(input_field,dtype=complex)
    if matrix.ndim!=2 or field.ndim!=1 or matrix.shape[1]!=field.size:
        raise ValueError('Use a 2-D matrix and a matching 1-D field vector')
    if not np.isfinite(matrix).all() or not np.isfinite(field).all():raise ValueError('Fields and matrix must be finite')
    return matrix@field


def powers(field):
    field=np.asarray(field,dtype=complex)
    if field.ndim!=1 or not np.isfinite(field).all():raise ValueError('Expected a finite 1-D complex field')
    return np.abs(field)**2


def to_lower_first(matrix):
    """Change both input/output order via P T P; theta remains on physical upper arm."""
    matrix=np.asarray(matrix,dtype=complex)
    if matrix.shape!=(2,2):raise ValueError('Expected a 2x2 matrix')
    return matrix[np.ix_([1,0],[1,0])].copy()


def theta_for_bar(power):
    power=_real(power,'power')
    if not 0<=power<=1:raise ValueError('bar fraction must be within [0, 1]')
    return float(2*np.arcsin(np.sqrt(power)))


def propagation_factor(neff,length_um,wavelength_um,loss_db=0.):
    """Uniform real-index segment; lengths and wavelength use the same units."""
    neff=_real(neff,'neff');length_um=_real(length_um,'length_um');wavelength_um=_real(wavelength_um,'wavelength_um')
    if neff<=0 or length_um<0 or wavelength_um<=0:raise ValueError('Require neff>0, length>=0, wavelength>0')
    return amplitude_factor(loss_db)*np.exp(2j*np.pi*neff*length_um/wavelength_um)


def trace(theta,phi,input_field,loss_db=0.,mmi_errors=(0.,0.)):
    """Copies of intermediate fields for a learner to inspect; no file I/O."""
    field=np.asarray(input_field,dtype=complex)
    if len(mmi_errors)!=2:raise ValueError('Provide one imbalance for each coupler')
    if field.shape!=(2,):raise ValueError('MZI requires two input fields')
    rows=[('input',field.copy())]
    stages=[('after_phi',phase_shift(phi)),('after_MMI1',coupler(mmi_errors[0])),
            ('after_theta',phase_shift(theta)),('after_MMI2',coupler(mmi_errors[1])),
            ('after_uniform_loss',np.eye(2)*amplitude_factor(loss_db))]
    for name,matrix in stages:
        field=apply_matrix(matrix,field);rows.append((name,field.copy()))
    return rows
