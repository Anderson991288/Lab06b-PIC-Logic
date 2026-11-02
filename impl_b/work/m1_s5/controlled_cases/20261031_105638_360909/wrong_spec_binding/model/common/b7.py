"""Five-mode, seven-MZI forward network built from the course topology.

OPS entries are (upper_mode_index, physical_layer). A local MZI acts on
(p, p+1), upper first. Lists follow light propagation; later matrices multiply
on the left. Bypass modes remain identity, including when MZI loss is enabled.
No PDK, wire propagation, reflection, heater or layout model is implied.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np
from . import mzi, linear_network as network


@dataclass(frozen=True)
class Topology:
    modes: int
    ops: tuple
    readout: tuple = (1, 3)

    def __post_init__(self):
        def integer(x): return isinstance(x, (int, np.integer)) and not isinstance(x, bool)
        if not integer(self.modes) or self.modes != 5:
            raise ValueError('This B7 requires five modes')
        if len(self.ops) != 7 or any(len(op) != 2 for op in self.ops):
            raise ValueError('Provide seven (upper mode, layer) entries')
        ops = tuple(tuple(op) for op in self.ops)
        if any(not integer(p) or not integer(layer) or not 0 <= p < 4 or not 0 <= layer < 4 for p, layer in ops):
            raise ValueError('Invalid adjacent-mode index or layer')
        if tuple(layer for p, layer in ops) != tuple(sorted(layer for p, layer in ops)):
            raise ValueError('OPS must follow physical layer order')
        if tuple(sum(layer == k for p, layer in ops) for k in range(4)) != (2, 1, 2, 2):
            raise ValueError('B7 layer populations must be 2,1,2,2')
        for k in range(4):
            ports = [q for p, layer in ops if layer == k for q in (p, p+1)]
            if len(set(ports)) != len(ports):
                raise ValueError('Two MZIs cannot share a mode within one layer')
        if len(self.readout) != 2 or any(not integer(q) or not 0 <= q < 5 for q in self.readout) or self.readout[0] == self.readout[1]:
            raise ValueError('Readout needs two distinct mode indices')
        object.__setattr__(self, 'ops', ops)
        object.__setattr__(self, 'readout', tuple(self.readout))


def load_topology(course_path=None):
    path = Path(course_path) if course_path else Path(__file__).resolve().parents[2]/'config/course.json'
    a = json.loads(path.read_text(encoding='utf-8'))['architecture']
    if a['macro'] != 'B7' or a['mzi_count'] != 7 or a['phase_count'] != 14:
        raise ValueError('Architecture does not describe the course B7')
    if a['inputs'] != ['x1','x2','x3','x4','R']:
        raise ValueError('Input field order must be x1,x2,x3,x4,R')
    return Topology(a['modes'], a['ops_zero_based'], a['readout_zero_based'])


def _seven(values, name, scalar=False):
    values = np.asarray(values, dtype=float)
    if scalar and values.ndim == 0: values = np.full(7, float(values))
    if values.shape != (7,) or not np.isfinite(values).all():
        raise ValueError(name+' must contain seven finite values')
    return values


def elements(topology, theta, phi, loss_db=0.):
    theta = _seven(theta, 'theta'); phi = _seven(phi, 'phi')
    losses = _seven(loss_db, 'loss_db', scalar=True)
    if np.any(losses < 0): raise ValueError('Passive MZI losses must be nonnegative')
    return [network.embed_2x2(mzi.T2(theta[k], phi[k], losses[k]), p, p+1, topology.modes)
            for k, (p, layer) in enumerate(topology.ops)]


def layers(topology, theta, phi, loss_db=0.):
    matrices = elements(topology, theta, phi, loss_db)
    return [network.cascade([matrices[k] for k, (p, layer) in enumerate(topology.ops) if layer == index], topology.modes)
            for index in range(4)]


def transfer_matrix(topology, theta, phi, loss_db=0.):
    return network.cascade(elements(topology, theta, phi, loss_db), topology.modes)


def trace(topology, theta, phi, input_field, loss_db=0., by_layer=False):
    field = np.asarray(input_field, dtype=complex)
    if field.shape != (topology.modes,) or not np.isfinite(field).all():
        raise ValueError('B7 input must be a finite five-mode field')
    stages = layers(topology, theta, phi, loss_db) if by_layer else elements(topology, theta, phi, loss_db)
    fields = network.propagate_stages(stages, field)
    labels = ['input'] + ([f'layer{k}' for k in range(4)] if by_layer else [f'M{k}' for k in range(1,8)])
    return list(zip(labels, fields))


def bypass_ports(topology):
    return [tuple(sorted(set(range(topology.modes)) - {q for p, layer in topology.ops if layer == index for q in (p,p+1)}))
            for index in range(4)]


def reachability(topology):
    """Structural possible paths, not guaranteed nonzero complex coefficients."""
    possible = np.eye(topology.modes, dtype=bool)
    for p, layer in topology.ops:
        combined = possible[p] | possible[p+1]
        possible[p] = combined; possible[p+1] = combined
    return possible
