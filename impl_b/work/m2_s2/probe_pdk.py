from pathlib import Path
import os,sys,json,inspect
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='1'
from cornerstone.technology import select_technology_variant,CornerstoneVariant
select_technology_variant(CornerstoneVariant.SOI220)
import cornerstone, cornerstone.all as cs, ipkiss
import numpy as np
c=cs.SOI220nm_1550nm_TE_STRIP_2x2_MMI();cm=c.CircuitModel();model=cm._generate_model()
print('VERSIONS',cornerstone.__version__,ipkiss.__version__)
print('CELL',inspect.getfile(type(c)),'VIEW',type(cm),inspect.getfile(type(cm)))
print('MODEL',type(model),inspect.getfile(type(model)))
print('MODEL_STATE',str(model))
S=cm.get_smatrix(wavelengths=np.array([1.55]),validate_netlist=True)
print('H',[[S[o,i][0] for i in ['in2','in1']] for o in ['out2','out1']])
print('PORTS',[(p.name,list(p.position)) for p in c.Layout().ports])
