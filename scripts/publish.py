#!/usr/bin/env python3
"""Publish/recover a draft; never replace an already published client asset."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import hashlib


def run(*args):
    return subprocess.run(list(map(str, args)), check=True)


def main():
    release = Path('release')
    if not release.exists():
        print('No release payload yet')
        return
    run('python3', 'scripts/verify.py')
    meta = json.loads((release / 'release.json').read_text())
    repo, tag = os.environ['GH_REPO'], meta['tag']
    result = subprocess.run(['gh', 'release', 'view', tag, '--repo', repo, '--json', 'isDraft'], capture_output=True, text=True)
    exists = result.returncode == 0
    if not exists and 'release not found' not in result.stderr.lower() and 'HTTP 404' not in result.stderr:
        raise RuntimeError(result.stderr)
    if exists and not json.loads(result.stdout)['isDraft']:
        with tempfile.TemporaryDirectory() as temp:
            run('gh', 'release', 'download', tag, '--repo', repo, '--dir', temp,
                '--pattern', 'release.json', '--pattern', 'hitry-slon.mrpack')
            if json.loads((Path(temp) / 'release.json').read_text()) != meta:
                raise ValueError('Published version already has different metadata')
            if hashlib.sha256((Path(temp) / 'hitry-slon.mrpack').read_bytes()).hexdigest() != meta['sha256']:
                raise ValueError('Published archive differs from the requested immutable release')
        print('Existing published release matches; no changes')
        return
    if not exists:
        run('gh', 'release', 'create', tag, '--repo', repo, '--target', os.environ['GITHUB_SHA'],
            '--draft', '--title', 'Hitry Slon ' + tag,
            '--notes', 'Импортируйте hitry-slon.mrpack в совместимый лаунчер. Версия должна совпадать с сервером.',
            '--prerelease' if meta['prerelease'] else '--prerelease=false')
    run('gh', 'release', 'upload', tag, '--repo', repo, '--clobber', release / 'hitry-slon.mrpack', release / 'release.json')
    run('gh', 'release', 'edit', tag, '--repo', repo, '--draft=false')


if __name__ == '__main__':
    main()
