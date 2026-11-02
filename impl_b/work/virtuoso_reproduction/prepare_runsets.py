from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;OUT=HERE/'out';BASE='/mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction'
template=(ROOT/'reference/C01/outputs/virtuoso_drc/B7_GUI.runset').read_text(encoding='utf-8')
for name,auto,cell,layout in [('auto',True,'lab06b_b7_ec_pad_chip','lab06b_b7_ec_pad_chip.calibre.db'),('fixed',False,'LAB06B_B7_EC_PAD_CHIP',BASE+'/out/exports_final/B7_crosscad_final.gds')]:
    folder=OUT/('gui_'+name);folder.mkdir(exist_ok=True)
    changes={'drc.rulesFile.value':'"'+BASE+'/out/rules/cornerstone_basic_draft.svrf"','drc.runDir.value':'"'+BASE+'/out/gui_'+name+'"','drc.layout.exportFromLayoutViewer.value':str(auto).lower(),'drc.layout.layoutFile.value':'"'+layout+'"','drc.layout.topCellLibrary.value':'"lab06b_crosscad_20261031"','cmn.layout.topCellLibraryFDI.value':'"lab06b_crosscad_20261031"','drc.layout.topCell.value':'"'+cell+'"'}
    s=template
    for key,value in changes.items():s=re.sub(r'^'+re.escape(key)+r'\s*=.*$',key+' = '+value,s,flags=re.M)
    s=s.replace('C01_B7_EC_PAD_CHIP',cell).replace('B7_LABELS','lab06b_crosscad_20261031')
    (OUT/('Lab06b_'+name+'.runset')).write_text(s,encoding='utf-8',newline='\n')
print('Prepared new auto-export and fixed-GDS Runsets')
