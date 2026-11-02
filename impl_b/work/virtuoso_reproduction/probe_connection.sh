#!/usr/bin/env bash
set -eu
python3 - <<'PY'
import os,json,socket
r={'license_environment':{k:os.environ.get(k) for k in ['CDS_LIC_FILE','LM_LICENSE_FILE','MGLS_LICENSE_FILE','SALT_LICENSE_SERVER']},'connections':{}}
for host in ['eda.ic','127.0.0.1']:
    for port in [5280,27017]:
        try:
            with socket.create_connection((host,port),timeout=2):r['connections'][host+':'+str(port)]='connected'
        except OSError as e:r['connections'][host+':'+str(port)]=str(e)
print(json.dumps(r,indent=2))
PY
