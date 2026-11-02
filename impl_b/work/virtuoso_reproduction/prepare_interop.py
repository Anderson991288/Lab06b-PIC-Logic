from pathlib import Path
import os,sys,json
HERE=Path(__file__).resolve().parent
HANDLE=os.add_dll_directory(str(Path(sys.prefix)/'Library/bin')) if os.name=='nt' else None
import gdstk
lib=gdstk.read_gds(str(HERE/'out/input/B7_source.gds'));names=[c.name for c in lib.cells];assert len({n.lower() for n in names})==len(names)
mapping={n.lower():n for n in names}
(HERE/'out/oa_cell_name_map.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')
(HERE/'out/exports/cell.map').write_text(''.join('lab06b_current_20261031 '+lower+' layout '+name+'\n' for lower,name in mapping.items()),encoding='utf-8',newline='\n')
(HERE/'out/exports/layer.map').write_text(''.join(f'L{n} drawing {n} 0\n' for n in [3,4,5,39,41,99,100,1002]),encoding='utf-8',newline='\n')
print('Prepared one-to-one OA lower-case -> original GDS cell-name map:',len(mapping))
