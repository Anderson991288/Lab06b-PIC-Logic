from pathlib import Path
import json,subprocess,hashlib,xml.etree.ElementTree as ET,collections
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
paths=load(ROOT/'EDA_paths.json');C=load(ROOT/'config/m2_verification.json');exe=ROOT/paths['windows']['klayout_exe'];deck=ROOT/C['deck'];size=load(ROOT/'work/m2_s5/out/chip_info.json')['chip_size_um']
def run(script,args,log):
    cmd=[str(exe),'-b','-r',str(script)]
    for k,v in args.items():cmd+=['-rd',str(k)+'='+str(v)]
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    log.parent.mkdir(parents=True,exist_ok=True);log.write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError(script.name+' failed: '+r.stderr[-1600:])
run(HERE/'generate_faults.py',{},OUT/'generate_faults.log')
results=[]
for fault in load(OUT/'fault_manifest.json'):
    folder=OUT/'controls'/fault['id'];folder.mkdir(parents=True,exist_ok=True);gds=ROOT/fault['path'];report=folder/'pre_drc.lyrdb'
    assert hashlib.sha256(gds.read_bytes()).hexdigest()==fault['sha256']
    run(deck,dict(input=gds,report=report,dw=size[0],dh=size[1]),folder/'pre_drc.log')
    tree=ET.parse(report);counts=collections.Counter((r.findtext('category') or '').strip("'") for r in tree.findall('.//items/item'))
    run(HERE/'check_connectivity.py',dict(gds_path=gds,result_path=folder/'connectivity.json'),folder/'connectivity.log')
    conn=load(folder/'connectivity.json')
    caught=any(fault['expected_category_fragment'] in name for name,count in counts.items() if count) if fault['target']=='drc' else not conn[fault['target']]['passed']
    result=dict(**fault,detected=bool(caught),drc_records=sum(counts.values()),drc_counts=dict(counts),electrical_passed=conn['electrical']['passed'],optical_passed=conn['optical']['passed'],
        optical_route_count=conn['optical']['route_components'],metal_net_count=conn['electrical']['metal_nets'],report=str(report.relative_to(ROOT)))
    results.append(result);print(fault['id'],'detected',bool(caught),'DRC',result['drc_records'],'metal',result['metal_net_count'],'optical',result['optical_route_count'],flush=True)
(OUT/'control_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
assert all(r['detected'] for r in results)
