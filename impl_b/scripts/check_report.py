from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from collections import Counter
import argparse
import hashlib
import json
import re


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.stack = []
        self.errors = []
        self.tables = 0
        self.captions = 0

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if 'id' in data:
            self.ids.append(data['id'])
        for attr in ['href', 'src']:
            if data.get(attr):
                self.links.append(data[attr])
        if tag == 'table':
            self.tables += 1
        if tag == 'caption':
            self.captions += 1
        if tag in ['section', 'table', 'figure', 'details', 'div', 'nav', 'aside', 'main']:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in ['section', 'table', 'figure', 'details', 'div', 'nav', 'aside', 'main']:
            if not self.stack or self.stack[-1] != tag:
                self.errors.append('Unbalanced ' + tag)
            else:
                self.stack.pop()


def run(root):
    report_path = root / 'evidence/report_checks.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text('{}', encoding='utf-8')
    docs = {}
    errors = []
    for path in root.rglob('*.html'):
        if path.relative_to(root).parts[0] in ('C01', 'history', '.codex', '.claude', 'tools'):
            continue
        text = path.read_text(encoding='utf-8-sig')
        doc = Document()
        doc.feed(text)
        docs[path.resolve()] = doc
        rel = path.relative_to(root).as_posix()
        if '\x00' in text or not text.strip().lower().startswith('<!doctype html>') or '</html>' not in text.lower():
            errors.append(rel + ': invalid document boundaries')
        if doc.stack or doc.errors:
            errors.append(rel + ': invalid nesting ' + str(doc.errors or doc.stack))
        duplicates = [i for i, n in Counter(doc.ids).items() if n > 1]
        if duplicates:
            errors.append(rel + ': duplicate IDs ' + str(duplicates))
        if doc.tables != doc.captions:
            errors.append(rel + ': table caption count mismatch')
    checked_links = 0
    for path, doc in docs.items():
        for link in doc.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            checked_links += 1
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(root.resolve()):
                errors.append(f'{path.name}: link escapes package: {link}')
            elif not target.exists():
                errors.append(f'{path.name}: missing local link: {link}')
            elif url.fragment and target in docs and unquote(url.fragment) not in docs[target].ids:
                errors.append(f'{path.name}: missing fragment: {link}')
    result = dict(status='passed' if not errors else 'failed', html_files=len(docs),
                  local_links_checked=checked_links, errors=errors,
                  note='Static UTF-8/document/nesting/ID/caption/local-link/fragment checks. Historical results are not revalidated EDA.')
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return not errors


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('root', type=Path)
    raise SystemExit(0 if run(p.parse_args().root) else 1)
