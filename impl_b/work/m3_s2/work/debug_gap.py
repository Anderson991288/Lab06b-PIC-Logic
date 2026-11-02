from pathlib import Path
import sys
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
from independent_geometry import *
from shapely.geometry import Point
m,_=read_material(ROOT/'work/m2_s6/out/after/b7_ec_pad.gds',3);m,a,b,t,n,edges,rings,ids,sizes=boundary_edges(m)
near=[k for k,e in enumerate(edges) if e.distance(Point(208.5,-15))<.4]
print('point inside',m.contains(Point(208.5,-15)),'edges',len(near))
for k in near:print(k,a[k],b[k],t[k],n[k],rings[k],ids[k])
for i in near:
 for j in near:
  if j<=i:continue
  line=shapely.shortest_line(edges[i],edges[j]);c=list(line.coords);v=np.array(c[1])-c[0];trim=LineString([np.array(c[0])+.01*v,np.array(c[1])-.01*v]);print('pair',i,j,line.length,np.dot(t[i],t[j]),np.dot(n[i],v),np.dot(n[j],v),'space',m.disjoint(trim),'width',m.covers(trim),c)
