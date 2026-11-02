"""Standalone consumer. Needs Python >=3.10 and NumPy; no course-root paths."""
from pathlib import Path
import os,sys,json,argparse
DLL_HANDLE=None
if os.name=='nt' and (Path(sys.prefix)/'Library/bin').is_dir():DLL_HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin'))
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'model'))
from common import handoff


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=HERE/'verification/replay_results.json')
    parser.add_argument('--gate',default='AND2');parser.add_argument('--bits',default='1100');args=parser.parse_args()
    spec,phases=handoff.load_bundle(HERE);results=handoff.replay(spec,phases)
    max_error=handoff.verify_truth_csv(HERE,results)
    if args.gate not in results or len(args.bits)!=4 or set(args.bits)-{'0','1'}:raise ValueError('Choose a supported gate and four binary bits')
    case=next(r for r in results[args.gate]['rows'] if r['pattern']==args.bits)
    report=dict(status='passed' if all(r['summary']['accepted'] for r in results.values()) else 'failed',bundle=str(HERE),
        python=sys.executable,loaded_model=str(Path(handoff.__file__).resolve()),
        files_verified=True,csv_max_error=max_error,truth_passed=sum(r['summary']['passed'] for r in results.values()),truth_total=80,
        summaries={g:r['summary'] for g,r in results.items()},
        example=dict(gate=args.gate,pattern=args.bits,positive_power=float(case['powers'][1]),negative_power=float(case['powers'][3]),delta=case['delta'],bit=case['bit'],expected=case['expected']))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
