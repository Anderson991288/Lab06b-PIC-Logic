"""Isolated actual-GDS comparison control; never overwrite accepted/rebuilt GDS."""
from pathlib import Path
import pya
source=Path(input_gds).resolve();dest=Path(output_gds).resolve()
if source==dest:raise ValueError('Fault must be a separate GDS')
l=pya.Layout();l.read(str(source));l.top_cell().shapes(l.layer(3,0)).insert(pya.Box(0,200000,10000,210000));l.write(str(dest))
print('Inserted an isolated 10 um Si square in a control copy')
