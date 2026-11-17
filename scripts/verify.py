#!/usr/bin/env python3
"""Verify public release payload before publishing assets."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--release-dir', type=Path, default=Path('release'))
release = parser.parse_args().release_dir
if not release.exists():
    print('No release payload yet; public repository structure valid')
    raise SystemExit(0)
meta = json.loads((release / 'release.json').read_text())
if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', meta['tag']):
    raise ValueError('Invalid release tag')
if not re.fullmatch(r'[0-9a-f]{40}', meta['source_commit']):
    raise ValueError('Invalid source commit')
if not isinstance(meta.get('prerelease'), bool) or meta['prerelease'] != ('-' in meta['tag']):
    raise ValueError('Invalid prerelease flag')
archive = release / 'hitry-slon.mrpack'
if hashlib.sha256(archive.read_bytes()).hexdigest() != meta['sha256']:
    raise ValueError('Release archive hash mismatch')
with zipfile.ZipFile(archive) as z:
    index = json.loads(z.read('modrinth.index.json'))
    if index['versionId'] != meta['tag'][1:]:
        raise ValueError('Version mismatch')
    if index['dependencies'] != {'minecraft': meta['minecraft'], 'neoforge': meta['neoforge']}:
        raise ValueError('Platform mismatch')
    for name in z.namelist():
        p = Path(name)
        if p.is_absolute() or '..' in p.parts:
            raise ValueError('Unsafe archive path')
        if name != 'modrinth.index.json' and not name.startswith(('overrides/config/', 'overrides/resourcepacks/', 'overrides/kubejs/')):
            raise ValueError(f'Unexpected public payload: {name}')
    for f in index['files']:
        if not f['path'].startswith('mods/') or Path(f['path']).name != f['path'][5:]:
            raise ValueError('Unsafe mod path')
        if f.get('env', {}).get('client') != 'required':
            raise ValueError('Server-only mod in public client payload')
        if not all(u.startswith('https://cdn.modrinth.com/') for u in f['downloads']):
            raise ValueError('Unexpected download source')
        if not any(re.fullmatch(rf'[0-9a-f]{{{n}}}', f['hashes'].get(algo,'')) for algo,n in [('sha256',64),('sha512',128)]):
            raise ValueError('Missing strong hash')
print('Public release payload verified:', meta['tag'])
