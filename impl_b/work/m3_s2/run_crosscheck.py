from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,sys,json,hashlib,subprocess,xml.etree.ElementTree as ET,csv,time,io,unittest,importlib.util,ast
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out';WORK=HERE/'work'
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='1'
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
sys.path.insert(0,str(HERE))
from independent_geometry import read_material,measure_facing,digest
from generate_controls import generate
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def main():
    cfg=load(ROOT/'config/m3_crosscheck.json');assert cfg['angle_limit_deg']==45 and cfg['deck_feature_margin_um']==-.001 and cfg['boundary_limit_shift_um']==1e-6 and cfg['visibility_numeric_tolerance_um']==1e-9
    current=load(ROOT/cfg['source_chip_index']);assert current['accepted_at_step']=='M2 S6'
    for p,h in current['files'].items():assert digest(ROOT/p)==h
    source=next(ROOT/p for p in current['files'] if p.endswith('.gds'));tools=load(ROOT/'EDA_paths.json')['windows'];deck=ROOT/tools['drc_deck'];exe=Path(tools['klayout_exe']);exe=exe if exe.is_absolute() else ROOT/exe
    assert digest(deck)==load(ROOT/'config/m2_verification.json')['deck_sha256']
    run=WORK/datetime.now().strftime('%Y%m%d_%H%M%S_%f');run.mkdir(parents=True)
    cases=[dict(id='accepted',gds=str(source),sha256=digest(source))]+generate(source,run/'controls');save(OUT/'case_inventory.json',cases)
    independents=[];audit=None
    for case in cases:
        layers=[]
        for c in cfg['layers']:
            material,meta=read_material(case['gds'],c['layer']);measured=measure_facing(material,c['width_search_cap_um'],c['space_search_cap_um'],cfg['angle_limit_deg'])
            for kind in ['width','space']:
                found=measured[kind]['minimum'];assert found is not None
                limit=c[kind+'_um']+cfg['deck_feature_margin_um'];measured[kind]['effective_limit_um']=limit;measured[kind]['rule_passed']=found['value_um']>=limit-1e-9
            layers.append(dict(layer=c['layer'],metadata=meta,measurements=measured))
            if case['id']=='accepted' and c['layer']==3:
                naive=measure_facing(material,c['width_search_cap_um'],c['space_search_cap_um'],cfg['angle_limit_deg'],False)
                audit=dict(issue='Closed-notch cap is a one-sided open-space limit; strict disjoint connector alone misses it',strict_connector_only_um=naive['space']['minimum']['value_um'],corrected_um=measured['space']['minimum']['value_um'],witness=measured['space']['minimum'],correction='Test both 1e-6 um perpendicular shifts when the trimmed connector is entirely on boundary; no change to measured distance or GDS')
        independents.append(dict(id=case['id'],gds_sha256=digest(case['gds']),layers=layers));print('Independent gdstk/Shapely:',case['id'],flush=True)
    save(OUT/'independent_results.json',independents);save(OUT/'method_difference.json',audit)
    def execute(script,args,log):
        cmd=[str(exe),'-b','-r',str(script)]
        for k,v in args.items():cmd+=['-rd',str(k)+'='+str(v)]
        start=time.monotonic();r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300);(OUT/log).write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
        if r.returncode:raise RuntimeError(script.name+' failed; '+r.stderr[-1000:])
        print(script.name,'passed',round(time.monotonic()-start,2),'s',flush=True)
    execute(HERE/'klayout_measure.py',{},'klayout_measure.log')
    # Re-run the entire unmodified installed deck, not just the six local probes.
    chip=load(next(ROOT/p for p in current['files'] if p.endswith('chip_info.json')));w,h=chip['chip_size_um']
    execute(deck,dict(input=source,report=OUT/'pre_drc.lyrdb',dw=w,dh=h),'original_pre_drc.log')
    native=load(OUT/'klayout_results.json');comparison=[];controls=[];rows=[]
    for independent,native_case,case in zip(independents,native,cases):
        assert independent['id']==native_case['id']==case['id'] and independent['gds_sha256']==native_case['gds_sha256']==case['sha256']
        for x,y,c in zip(independent['layers'],native_case['layers'],cfg['layers']):
            assert x['layer']==y['layer']==c['layer']
            area_error=abs(x['metadata']['area_um2']-y['area_um2']);assert area_error<cfg['area_tolerance_um2']
            assert x['metadata']['merged_components']==y['merged_components'] and max(abs(a-b) for a,b in zip(x['metadata']['bbox_um'],y['bbox_um']))<1e-8
            for kind in ['width','space']:
                v=x['measurements'][kind];k=y['metrics'][kind];value=v['minimum']['value_um'];agree=v['rule_passed']==k['rule_passed']
                row=dict(case=case['id'],layer=x['layer'],kind=kind,nominal_um=c[kind+'_um'],effective_limit_um=k['effective_limit_um'],independent_um=value,independent_rule_passed=v['rule_passed'],KLayout_rule_passed=k['rule_passed'],KLayout_violations=k['violations'],rule_agreement=agree)
                if case['id']=='accepted':
                    low,high=k['lower_bound_um'],k['upper_bound_um'];distance=max(low-value,0,value-high);row.update(KLayout_lower_um=low,KLayout_upper_um=high,interval_distance_um=distance,numeric_agreement=distance<=cfg['comparison_tolerance_um'],area_error_um2=area_error,witness=v['minimum'])
                    comparison.append(row)
                rows.append(row);assert agree,(case['id'],x['layer'],kind)
                if case['id']!='accepted' and case['layer']==x['layer'] and case['kind']==kind:
                    controls.append(dict(id=case['id'],layer=x['layer'],kind=kind,inserted_dimension_um=case['inserted_dimension_um'],expected_rule_passed=case['expected_rule_passed'],independent_rule_passed=v['rule_passed'],KLayout_rule_passed=k['rule_passed'],independent_um=value,passed=v['rule_passed']==k['rule_passed']==case['expected_rule_passed'],gds_sha256=case['sha256']))
    s=importlib.util.spec_from_file_location('geometry_tests',HERE/'test_independent_geometry.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);stream=io.StringIO();t=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(m.IndependentGeometryTests));(OUT/'unit_tests.log').write_text(stream.getvalue(),encoding='utf-8')
    with (OUT/'comparison_54.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['case','layer','kind','nominal_um','effective_limit_um','independent_um','independent_rule_passed','KLayout_rule_passed','KLayout_violations','rule_agreement','KLayout_lower_um','KLayout_upper_um','interval_distance_um'];writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    count=len(ET.parse(OUT/'pre_drc.lyrdb').findall('.//items/item'));categories=len(ET.parse(OUT/'pre_drc.lyrdb').findall('.//categories/category'))
    tree=ast.parse((HERE/'independent_geometry.py').read_text(encoding='utf-8'));imports=[n.module if isinstance(n,ast.ImportFrom) else a.name for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom)) for a in ([None] if isinstance(n,ast.ImportFrom) else n.names)]
    assert not any(n and n.split('.')[0] in ['pya','klayout','ipkiss','ipkiss3'] for n in imports)
    checks=[('accepted_six_numeric_agreements',len(comparison)==6 and all(r['numeric_agreement'] and r['rule_agreement'] and r['independent_rule_passed'] for r in comparison)),('54_rule_comparisons',len(rows)==54 and all(r['rule_agreement'] for r in rows)),('eight_real_GDS_controls',len(controls)==8 and all(c['passed'] for c in controls)),('original_full_pre_DRC_zero',count==0 and categories==31),('notch_correction_exercised',audit['strict_connector_only_um']>audit['corrected_um'] and abs(audit['corrected_um']-.53)<1e-9),('independent_reader_imports',True),('geometry_tests',t.wasSuccessful())]
    sources=['config/m3_crosscheck.json',*['work/m3_s2/'+p for p in ['independent_geometry.py','generate_controls.py','klayout_measure.py','run_crosscheck.py','test_independent_geometry.py']]]
    result=dict(step='M3 S2',timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),status='passed' if all(v for k,v in checks) else 'failed',gds_sha256=digest(source),deck_sha256=digest(deck),config=cfg,comparison=comparison,controls=controls,method_difference=audit,
        pre_DRC_records=count,pre_DRC_categories=categories,tests=dict(run=t.testsRun,passed=t.testsRun-len(t.failures)-len(t.errors),successful=t.wasSuccessful()),checks=[dict(name=k,passed=bool(v)) for k,v in checks],rule_comparisons=len(rows),
        source_hashes={p:digest(ROOT/p) for p in sources},independent_imports=imports,physical_function_qualified=False,foundry_full_signoff=False,D_writes=False,
        scope=cfg['scope'],course_core_steps_implemented=17,learner_submission='pending',next_step='learner independent submission and instructor review')
    save(OUT/'crosscheck_results.json',result);assert result['status']=='passed';print('M3 S2 accepted: 6 measurements, 54 rule comparisons, 8 GDS controls, tests',t.testsRun,flush=True)
if __name__=='__main__':OUT.mkdir(parents=True,exist_ok=True);main()
