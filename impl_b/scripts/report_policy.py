"""Reader policy: omit learner submission/acceptance sections and worksheets.

Applied at HTML output, so legacy evidence and computational sources stay intact.
"""
from html.parser import HTMLParser
from urllib.parse import urlsplit
import re
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
class Node:
    def __init__(self,tag,attrs,start,parent=None):self.tag=tag;self.attrs=dict(attrs);self.start=start;self.end=None;self.parent=parent;self.children=[]
class Tree(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=False);self.text=text;self.offsets=[0];self.nodes=[];self.stack=[]
        for m in re.finditer('\n',text):self.offsets.append(m.end())
        self.feed(text)
    def pos(self):line,col=self.getpos();return self.offsets[line-1]+col
    def handle_starttag(self,tag,attrs):
        start=self.pos();parent=self.stack[-1] if self.stack else None;n=Node(tag,attrs,start,parent);self.nodes.append(n)
        if parent:parent.children.append(n)
        if tag in VOID:n.end=start+len(self.get_starttag_text())
        else:self.stack.append(n)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i].tag==tag:
                self.stack[i].end=self.text.find('>',self.pos())+1;self.stack=self.stack[:i];return
def plain(text):return re.sub('<[^>]+>','',text)
def in_node(node,parent):return node.start>=parent.start and node.end is not None and node.end<=parent.end
def end_call(text,opening):
    depth=0;quote=None;escaped=False;i=opening
    while i<len(text):
        c=text[i]
        if quote:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c==quote:quote=None
        elif c in ['"',"'",'`']:quote=c
        elif c=='(':depth+=1
        elif c==')':
            depth-=1
            if depth==0:return i+1+(i+1<len(text) and text[i+1]==';')
        i+=1
    raise ValueError('Unbalanced worksheet event handler')
def clean_course_html(text):
    tree=Tree(text);ranges=[];removed_ids=set();removed_sections=set()
    forms=[]
    for n in tree.nodes:
        if n.tag=='section' and n.end and '學員姓名' in text[n.start:n.end]:forms.append(n)
    for n in tree.nodes:
        if n.tag!='h2' or not n.end:continue
        label=plain(text[n.start:n.end])
        boundary=min([q.start for q in tree.nodes if q.start>n.start and q.tag in ['h2','footer']]+[len(text)])
        id_=n.attrs.get('id')
        if not (id_=='submit' or (id_=='acceptance' and ('學員' in label or '學員提交' in text[n.end:boundary]))):continue
        section_forms=[f for f in forms if n.start<f.start<boundary]
        stop=max(f.end for f in section_forms) if section_forms else boundary
        if id_=='acceptance' and '學員' not in label:
            blocks=[q for q in tree.nodes if q.tag=='div' and q.start>=n.end and q.end and q.end<=boundary]
            if blocks:stop=blocks[0].end
        ranges.append((n.start,stop));removed_sections.add(n.attrs.get('id'))
    for form in forms:ranges.append((form.start,form.end))
    for n in tree.nodes:
        if n.attrs.get('id') and any(a<=n.start<b for a,b in ranges):removed_ids.add(n.attrs['id'])
    # Remove direct worksheet click handlers, including those in shared IIFEs;
    # leave all numerical model and diagnostic handlers byte-for-byte intact.
    for n in tree.nodes:
        if n.tag!='script' or not n.end:continue
        raw=text[n.start:n.end]
        for id_ in removed_ids:
            escaped=re.escape(id_)
            pattern=r'document\.(?:querySelector\([\'\"]#'+escaped+r'[\'\"]\)|getElementById\([\'\"]'+escaped+r'[\'\"]\))\.addEventListener\s*\('
            for match in re.finditer(pattern,raw):
                start=n.start+match.start();opening=n.start+match.end()-1;ranges.append((start,end_call(text,opening)))
    for n in tree.nodes:
        if n.tag!='a' or not n.end:continue
        href=n.attrs.get('href','');url=urlsplit(href)
        if not url.path and url.fragment in removed_sections:ranges.append((n.start,n.end))
        if re.search(r'(?:^|/)learner/.*observations(?:\.template)?\.json$',url.path):ranges.append((n.start,n.end))
    # Coalesce before editing; keep all technical headings and next-step content.
    merged=[]
    for start,stop in sorted(ranges):
        if merged and start<=merged[-1][1]:merged[-1]=(merged[-1][0],max(stop,merged[-1][1]))
        else:merged.append((start,stop))
    for start,stop in reversed(merged):text=text[:start]+text[stop:]
    return text
