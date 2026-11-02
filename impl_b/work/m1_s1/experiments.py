"""Small optical experiments using the M0 S3 matrices unchanged."""
import numpy as np
from common import mzi, linear_network as net, encoding


def and2(bits, relative_phase=0., threshold=1., loss_db=0.):
    field = encoding.ook_fields(bits, phases=[0., relative_phase])
    if field.size != 2:
        raise ValueError('AND2 needs two bits')
    out = mzi.apply_matrix(mzi.T2(np.pi/2, 0., loss_db), field)
    return field, out, net.power_difference_readout(out, 0, 1, threshold)


def nand_matrix():
    """Lossless three-mode network; output 0 is q*(-x1-x2+R)/sqrt(3).

    First mix data modes (0,1); then mix mode 0 with reference mode 2.
    q is a common unit-modulus phase. All three output powers are retained.
    """
    stages = [net.embed_2x2(mzi.T2(np.pi/2, 0.), 0, 1, 3),
              net.embed_2x2(mzi.T2(2*np.arcsin(np.sqrt(2/3)), np.pi/4), 0, 2, 3)]
    return net.cascade(stages, 3)


def nand2(bits, reference_amplitude=2., reference_phase=0., threshold=1/6):
    if len(bits) != 2:
        raise ValueError('NAND2 needs two bits')
    threshold = float(threshold)
    if not np.isfinite(threshold):
        raise ValueError('threshold must be finite')
    field = encoding.with_reference(bits, reference_amplitude, reference_phase)
    out = mzi.apply_matrix(nand_matrix(), field)
    power = float(mzi.powers(out)[0])
    margin = power-threshold
    return field, out, {'power': power, 'margin': margin,
                        'bit': None if abs(margin) <= 1e-10 else int(margin > 0)}
