"""Keep the canonical C-root and D-read-only policy visible on report rebuild."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
for rel in ['Lab06b_index.html','course/plan.html','reference/source_context.html']:
    p=ROOT/rel;text=p.read_text(encoding='utf-8');prefix='../' if '/' in rel else ''
    marker='<!-- CROOT:POLICY -->'
    panel=marker+'<div class="callout"><b>正式工作位置：</b>C:\\EDA_Codex\\Lab06b。之後只在 C:\\EDA_Codex 修改課程；D 槽唯讀。<a href="'+prefix+'evidence/c_path_verification.json">C 槽重跑及 D 槽還原紀錄</a></div><!-- /CROOT:POLICY -->'
    if marker not in text:text=text.replace('</h1>','</h1>'+panel,1)
    p.write_text(text,encoding='utf-8')
