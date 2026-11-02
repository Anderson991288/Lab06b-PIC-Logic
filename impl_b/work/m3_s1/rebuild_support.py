"""Strict GDS timestamp-only digest and clean-source boundary helpers."""
from pathlib import Path,PurePosixPath
import hashlib,struct
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def normalized_gds_bytes(data):
    data=bytearray(data);offset=0;changed=0;end=False
    while offset<len(data):
        if offset+4>len(data):raise ValueError('Truncated GDS record header')
        size,kind=struct.unpack_from('>HH',data,offset)
        if size<4 or size%2 or offset+size>len(data):raise ValueError('Invalid GDS record length')
        if kind in (0x0102,0x0502):
            if size!=28:raise ValueError('Invalid GDS date record')
            data[offset+4:offset+28]=struct.pack('>12h',*(2000,1,1,0,0,0)*2);changed+=1
        if kind==0x0400:
            if offset+size!=len(data):raise ValueError('Trailing bytes after ENDLIB')
            end=True
        offset+=size
    if not end or changed<2:raise ValueError('Incomplete GDS library')
    return bytes(data),changed
def normalized_digest(path):
    data,count=normalized_gds_bytes(Path(path).read_bytes())
    return dict(sha256=hashlib.sha256(data).hexdigest(),date_records=count,policy='Only BGNLIB/BGNSTR date payloads normalized to 2000-01-01; all other bytes retained')
def safe_source_path(value):
    p=PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:raise ValueError('Unsafe source path')
    if 'out' in p.parts or value.endswith(('.gds','.lyrdb','.zip','.pyc')):raise ValueError('Generated output cannot seed a clean build')
    return p
def reserve_empty_target(target,allowed_root):
    target=Path(target).resolve();allowed_root=Path(allowed_root).resolve()
    if not target.is_relative_to(allowed_root) or target==allowed_root:raise ValueError('Build target must stay inside the declared scratch root')
    if target.exists():raise ValueError('Build target already exists; refuse stale output reuse')
    target.mkdir(parents=True)
    return target
