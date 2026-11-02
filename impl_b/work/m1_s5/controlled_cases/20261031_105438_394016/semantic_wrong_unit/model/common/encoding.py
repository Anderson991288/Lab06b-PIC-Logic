"""Coherent on-off field encoding. Powers are in normalized power units.

One data bit 1 has power on_power; bit 0 has exactly zero field.
Reference amplitude is a FIELD amplitude, not a power. No per-pattern
normalization is performed. All phases are radians.
"""
import numpy as np


def _real(value, name, positive=False):
    value = float(value)
    if not np.isfinite(value) or (positive and value <= 0):
        raise ValueError(name + ' must be finite' + (' and positive' if positive else ''))
    return value


def ook_fields(bits, on_power=1., phases=None):
    bits = np.asarray(bits)
    if bits.ndim != 1 or bits.size == 0 or not np.isin(bits, [0, 1]).all():
        raise ValueError('bits must be a nonempty 1-D array containing only 0 and 1')
    on_power = _real(on_power, 'on_power', positive=True)
    phase = np.zeros(bits.size) if phases is None else np.asarray(phases, dtype=float)
    if phase.shape != bits.shape or not np.isfinite(phase).all():
        raise ValueError('phases must be finite and match bits')
    return np.sqrt(on_power) * bits.astype(float) * np.exp(1j * phase)


def with_reference(bits, reference_amplitude=3., reference_phase=0., on_power=1., phases=None):
    """Append the reference: four bits give [x1, x2, x3, x4, R]."""
    amplitude = _real(reference_amplitude, 'reference_amplitude')
    if amplitude < 0:
        raise ValueError('reference_amplitude must be nonnegative')
    phase = _real(reference_phase, 'reference_phase')
    return np.append(ook_fields(bits, on_power, phases), amplitude * np.exp(1j * phase))
