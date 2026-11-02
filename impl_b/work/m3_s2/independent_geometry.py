"""Independent gdstk/GEOS readback and facing-boundary distance measurement.

No pya, IPKISS, sidecar-generated geometry, or KLayout polygon export is used.
Width/space are minimum visible opposing-edge separations with >135-degree
directed edge angle; this scoped construction is NOT a full DRC implementation.
"""
from pathlib import Path
import math,hashlib
import numpy as np
import gdstk,shapely
from shapely.geometry import Polygon,LineString
from shapely import STRtree
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_material(path,layer,datatype=0):
    lib=gdstk.read_gds(str(path));tops=lib.top_level()
    if len(tops)!=1:raise ValueError('One top cell required')
    scale=lib.unit/1e-6;raw=tops[0].get_polygons(layer=layer,datatype=datatype)
    polys=[Polygon(p.points*scale) for p in raw]
    if not polys or any(not p.is_valid for p in polys):raise ValueError('Missing or invalid raw GDS polygon')
    material=shapely.union_all(polys)
    if not material.is_valid:raise ValueError('Invalid merged material; no silent repair')
    return material,dict(reader='gdstk '+gdstk.__version__,geometry_engine='Shapely '+shapely.__version__+' / GEOS '+shapely.geos_version_string,
        source_sha256=digest(path),top_cell=tops[0].name,library_unit_m=lib.unit,precision_um=lib.precision/1e-6,layer=layer,datatype=datatype,raw_polygons=len(polys),raw_vertices=sum(len(p.exterior.coords)-1 for p in polys),
        area_um2=float(material.area),perimeter_um=float(material.length),bbox_um=list(material.bounds),merged_components=len(material.geoms) if hasattr(material,'geoms') else 1,
        holes=sum(len(p.interiors) for p in (material.geoms if hasattr(material,'geoms') else [material])))
def boundary_edges(material):
    material=shapely.orient_polygons(material,exterior_cw=False);a=[];b=[];ring_ids=[];edge_ids=[];ring_sizes=[];ring=0
    for poly in material.geoms if hasattr(material,'geoms') else [material]:
        for boundary in [poly.exterior,*poly.interiors]:
            points=np.asarray(boundary.coords)
            for k,(x,y) in enumerate(zip(points[:-1],points[1:])):
                if np.linalg.norm(y-x)<1e-10:continue
                a.append(x);b.append(y);ring_ids.append(ring);edge_ids.append(k);ring_sizes.append(len(points)-1)
            ring+=1
    a=np.array(a);b=np.array(b);v=b-a;length=np.linalg.norm(v,axis=1);t=v/length[:,None];n=np.column_stack((-t[:,1],t[:,0]));edges=shapely.linestrings(np.stack([a,b],axis=1))
    return material,a,b,t,n,edges,np.array(ring_ids),np.array(edge_ids),np.array(ring_sizes)
def measure_facing(material,width_cap_um,space_cap_um,angle_limit_deg=45,include_boundary_limits=True):
    material,a,b,t,n,edges,ring_ids,edge_ids,sizes=boundary_edges(material);tree=STRtree(edges)
    pairs=tree.query(edges,predicate='dwithin',distance=max(width_cap_um,space_cap_um));i,j=pairs;keep=j>i;i,j=i[keep],j[keep]
    # Adjacent edges share a vertex, not an independent width or clearance.
    step=np.abs(edge_ids[i]-edge_ids[j]);adj=(ring_ids[i]==ring_ids[j])&((step<=1)|(step==sizes[i]-1))
    opposed=np.sum(t[i]*t[j],axis=1)<-math.cos(math.radians(angle_limit_deg))-1e-12
    i,j=i[~adj&opposed],j[~adj&opposed]
    lines=shapely.shortest_line(edges[i],edges[j]);p=shapely.get_point(lines,0);q=shapely.get_point(lines,1)
    p=np.column_stack([shapely.get_x(p),shapely.get_y(p)]);q=np.column_stack([shapely.get_x(q),shapely.get_y(q)]);v=q-p;d=np.linalg.norm(v,axis=1)
    ni=np.sum(n[i]*v,axis=1);nj=np.sum(n[j]*v,axis=1);shapely.prepare(material)
    # Visibility-only numerical guard for rotated cap lines; measured endpoints
    # and distances stay untouched. 1e-9 um is one millionth of the 1 nm GDS grid.
    width_visibility=material.buffer(1e-9);shapely.prepare(width_visibility)
    result={}
    for kind,mask,cap in [('width',(ni>1e-9)&(nj<-1e-9),width_cap_um),('space',(ni<-1e-9)&(nj>1e-9),space_cap_um)]:
        candidates=np.where(mask&(d>1e-9)&(d<=cap+1e-10))[0];ordered=candidates[np.argsort(d[candidates],kind='stable')];found=None;tested=0
        for start in range(0,len(ordered),128):
            ids=ordered[start:start+128];trimmed=shapely.linestrings(np.stack([p[ids]+.01*v[ids],q[ids]-.01*v[ids]],axis=1))
            visible=shapely.covers(width_visibility,trimmed) if kind=='width' else shapely.disjoint(material,trimmed)
            one_sided=np.zeros(len(ids),dtype=bool)
            if kind=='space' and include_boundary_limits:
                # A closed notch has its minimum at a cap edge. The limiting
                # connector lies ON material boundary; its open-space one-sided
                # limit must be tested, not silently excluded as an intersection.
                boundary_limit=shapely.covers(material,trimmed)&~shapely.contains_properly(material,trimmed)
                selected=np.flatnonzero(boundary_limit&~visible)
                if len(selected):
                    kk=ids[selected];shift=np.column_stack([-v[kk,1],v[kk,0]])/d[kk,None]*1e-6
                    for sign in [-1,1]:
                        moved=shapely.linestrings(np.stack([p[kk]+.01*v[kk]+sign*shift,q[kk]-.01*v[kk]+sign*shift],axis=1))
                        one_sided[selected]|=shapely.disjoint(material,moved)
                    visible|=one_sided
            tested+=len(ids)
            good=np.flatnonzero(visible)
            if len(good):
                k=int(ids[good[0]])
                angle=math.degrees(math.acos(float(np.clip(np.dot(t[i[k]],t[j[k]]),-1,1))))
                found=dict(value_um=float(d[k]),point_A_um=p[k].tolist(),point_B_um=q[k].tolist(),edge_A_um=[a[i[k]].tolist(),b[i[k]].tolist()],edge_B_um=[a[j[k]].tolist(),b[j[k]].tolist()],directed_angle_deg=angle,visibility='one_sided_boundary_limit' if one_sided[good[0]] else 'open_connector')
                break
        result[kind]=dict(minimum=found,search_cap_um=cap,candidate_pairs=len(candidates),visibility_tested=tested,scope='Minimum positive visible opposing-edge separation in declared search cap; adjacent edges excluded, >135-degree directed edge angle for angle_limit=45; not complete process DRC')
    result['boundary_edges']=len(edges);result['opposed_pairs']=len(i);return result
