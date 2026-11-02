"""Unedited actual Linux X11 client windows, selected by live titles."""
from pathlib import Path
import subprocess,re,json,sys
OUT=Path(__file__).resolve().parent/'out';(OUT/'screenshots').mkdir(exist_ok=True)
pattern,stem=sys.argv[1:]
listing=subprocess.run(['xwininfo','-root','-tree'],capture_output=True,text=True,check=True,env={**__import__('os').environ,'LC_ALL':'C.utf8'}).stdout
matches=[(wid,title) for wid,title in re.findall(r'^\s+(0x[0-9a-f]+) "([^\n"]+)"',listing,re.M) if re.search(pattern,title)]
assert matches,pattern
records=[]
for i,(wid,title) in enumerate(matches):
 file=OUT/'screenshots'/(stem+('' if len(matches)==1 else '_'+str(i))+'.png')
 subprocess.run(['import','-window',wid,str(file)],check=True)
 records.append(dict(method='Native Linux X11 ImageMagick client capture, unedited pixels',window_id=wid,title=title,file=file.relative_to(OUT).as_posix()))
(OUT/'screenshots'/(stem+'.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2))
print(records)
