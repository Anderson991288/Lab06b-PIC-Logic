"""Ideal DC receiver: matched PDs, declared positive differential gain.

The optical model uses normalized power. power_unit_w converts one such unit
to watts. Responsivity and transimpedance are illustrative calibration inputs,
not specifications of a selected detector. No bandwidth/noise/saturation model.
"""
import numpy as np
from .linear_network import power_difference_readout


def differential_receiver(field, positive, negative, power_unit_w=1e-6,
                          responsivity_a_per_w=.8, transimpedance_v_per_a=1e4,
                          threshold=0., epsilon=1e-10):
    values = [float(v) for v in (power_unit_w, responsivity_a_per_w, transimpedance_v_per_a)]
    if not np.isfinite(values).all() or min(values) <= 0:
        raise ValueError('Power scale, responsivity and transimpedance must be finite and positive')
    unit, response, gain = values
    result = power_difference_readout(field, positive, negative, threshold, epsilon)
    result.update(positive_current_a=result['positive_power'] * unit * response,
                  negative_current_a=result['negative_power'] * unit * response,
                  differential_current_a=result['delta'] * unit * response,
                  differential_voltage_v=result['delta'] * unit * response * gain,
                  threshold_voltage_v=float(threshold) * unit * response * gain,
                  voltage_margin_v=result['margin'] * unit * response * gain)
    return result
