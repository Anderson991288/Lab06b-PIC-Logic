"""Portable external KLayout recheck; proprietary deck is supplied separately."""
from pathlib import Path
import argparse,subprocess,json,xml.etree.ElementTree as ET
from verify_delivery import ROOT,verify,sha,load
def recheck(klayout,deck,out):
    verify(ROOT);manifest=load(ROOT/'manifest.json');deck=Path(deck).resolve();assert sha(deck)==manifest['external_deck_sha256'],'Requires the recorded external pre-DRC deck version'
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);info=load(ROOT/'data/chip_info.json');w,h=info['chip_size_um']
    commands=[([str(klayout),'-b','-r',str(deck),'-rd','input='+str(ROOT/'layout/B7_final.gds'),'-rd','report='+str(out/'pre_drc.lyrdb'),'-rd','dw='+str(w),'-rd','dh='+str(h)],'pre_drc'),
        ([str(klayout),'-b','-r',str(ROOT/'geometry_engine.py'),'-rd','bundle_root='+str(ROOT),'-rd','output_json='+str(out/'connectivity.json')],'connectivity')]
    for cmd,name in commands:
        r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);(out/(name+'.log')).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
        if r.returncode:raise RuntimeError(name+' execution failed')
    count=len(ET.parse(out/'pre_drc.lyrdb').findall('.//items/item'));conn=load(out/'connectivity.json');assert count==0 and conn['passed']
    result=dict(status='passed',pre_DRC_records=count,metal_nets=conn['electrical']['metal_nets'],optical_connections=conn['optical']['route_components'],foundry_full_signoff=False)
    (out/'portable_geometry.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--klayout',type=Path,required=True);p.add_argument('--deck',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(recheck(a.klayout,a.deck,a.out),indent=2))
