"""Explain coherent row sums and a fixed two-port power difference.

Terms are U[i,j]*v[j], without conjugating U. Pair interference contributions
are signed powers. No per-pattern normalization or optical model I/O occurs.
"""
import numpy as np
from .linear_network import power_difference_readout


def _matrix(matrix):
    matrix=np.asarray(matrix,dtype=complex)
    if matrix.ndim!=2 or min(matrix.shape)<1 or not np.isfinite(matrix).all():
        raise ValueError('Expected a finite, nonempty 2-D complex matrix')
    return matrix


def _index(index,n):
    if not isinstance(index,(int,np.integer)) or isinstance(index,bool) or not 0<=index<n:
        raise ValueError('Output index is outside the matrix')
    return int(index)


def row_contributions(matrix,input_field,output):
    matrix=_matrix(matrix);output=_index(output,matrix.shape[0])
    field=np.asarray(input_field,dtype=complex)
    if field.shape!=(matrix.shape[1],) or not np.isfinite(field).all():
        raise ValueError('Expected a matching finite 1-D input field')
    terms=matrix[output]*field
    cumulative=np.cumsum(terms)
    self_terms=np.abs(terms)**2
    pairs=[dict(j=j,k=k,power=float(2*np.real(terms[j]*terms[k].conjugate())))
           for j in range(len(terms)) for k in range(j+1,len(terms))]
    coherent_field=complex(sum(terms));coherent_power=float(abs(coherent_field)**2)
    return dict(output=output,coefficients=matrix[output].copy(),input_field=field.copy(),
                terms=terms.copy(),cumulative=cumulative,field=coherent_field,power=coherent_power,
                self_powers=self_terms,self_power=float(sum(self_terms)),pairs=pairs,
                interference_power=float(sum(p['power'] for p in pairs)))


def difference_operator(matrix,positive=1,negative=3):
    matrix=_matrix(matrix);positive=_index(positive,matrix.shape[0]);negative=_index(negative,matrix.shape[0])
    if positive==negative:raise ValueError('Readout ports must be distinct')
    return np.outer(matrix[positive].conjugate(),matrix[positive])-np.outer(matrix[negative].conjugate(),matrix[negative])


def evaluate(matrix,input_field,positive=1,negative=3,threshold=0.,epsilon=1e-10):
    plus=row_contributions(matrix,input_field,positive)
    minus=row_contributions(matrix,input_field,negative)
    matrix=_matrix(matrix);field=plus['input_field'];output=matrix@field
    readout=power_difference_readout(output,positive,negative,threshold,epsilon)
    Q=difference_operator(matrix,positive,negative)
    return dict(output_field=output,output_powers=np.abs(output)**2,positive=plus,negative=minus,
                readout=readout,operator=Q,quadratic_delta=float(np.real(field.conj()@Q@field)),
                self_delta=plus['self_power']-minus['self_power'],
                interference_delta=plus['interference_power']-minus['interference_power'])
