#!/usr/bin/env python3
"""Verify every frozen task file and reject extra files; never edit the source."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--manifest', type=Path, default=Path(__file__).with_name('RELEASE-MANIFEST.json'))
    a = p.parse_args()
    root = a.source.resolve(strict=True)
    records = json.loads(a.manifest.read_text())['files']
    expected = {r['path']: r for r in records}
    actual = {str(f.relative_to(root)) for f in root.rglob('*') if f.is_file() or f.is_symlink()}
    if actual != set(expected):
        raise SystemExit(json.dumps({'missing': sorted(set(expected)-actual), 'extra': sorted(actual-set(expected))}))
    for relative, r in sorted(expected.items()):
        rel = PurePosixPath(relative)
        if rel.is_absolute() or '..' in rel.parts:
            raise SystemExit('Unsafe manifest path')
        f = root.joinpath(*rel.parts)
        if f.is_symlink() or not f.is_file() or not f.resolve().is_relative_to(root):
            raise SystemExit('Unsafe source member: ' + relative)
        h = hashlib.sha256()
        with f.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                h.update(block)
        if f.stat().st_size != r['size_bytes'] or h.hexdigest() != r['sha256']:
            raise SystemExit('Source mismatch: ' + relative)
    print(json.dumps({'verified': True, 'task_count': len({x.split('/')[0] for x in expected}),
                      'file_count': len(expected), 'extra_files': 0, 'source_modified': False}))


if __name__ == '__main__':
    main()
