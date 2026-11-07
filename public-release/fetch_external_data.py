#!/usr/bin/env python3
"""Fetch exact official assets into a cache, optionally fill a derivative staging tree.

No credentials, source edits, existing-file overwrites, or score changes.
Use --offline with a populated cache to verify hydration without network access.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import urllib.request


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('DATA-PROVENANCE.json'))
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--hydrate', type=Path, help='Optional derivative task-source root; existing files must match and are not overwritten')
    parser.add_argument('--only', action='append', help='Asset ID; repeat for multiple assets; default all')
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    assets = json.loads(args.manifest.read_text())['assets']
    if args.only:
        if set(args.only) - {a['asset_id'] for a in assets}:
            parser.error('Unknown asset ID')
        assets = [a for a in assets if a['asset_id'] in args.only]
    args.cache.mkdir(parents=True, exist_ok=True)
    staging = None
    if args.hydrate:
        args.hydrate.mkdir(parents=True, exist_ok=True)
        staging = args.hydrate.resolve()
    receipt = []
    for asset in assets:
        blob = args.cache / asset['payload_sha256']
        if blob.exists():
            payload = blob.read_bytes()
        else:
            if args.offline:
                parser.error('Offline cache missing asset: ' + asset['asset_id'])
            with urllib.request.urlopen(asset['upstream_url'], timeout=90) as response:
                raw = response.read()
            if len(raw) != asset['download_size_bytes'] or sha(raw) != asset['download_sha256']:
                raise ValueError('Official download no longer matches frozen identity: ' + asset['asset_id'])
            if asset['archive_member']:
                with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                    member = archive.getmember(asset['archive_member'])
                    if not member.isfile():
                        raise ValueError('Expected regular archive member')
                    payload = archive.extractfile(member).read()
            else:
                payload = raw
        if len(payload) != asset['payload_size_bytes'] or sha(payload) != asset['payload_sha256']:
            raise ValueError('Payload does not match frozen source: ' + asset['asset_id'])
        if not blob.exists():
            with blob.open('xb') as output:
                output.write(payload)
        hydrated = []
        if staging:
            for relative in asset['canonical_paths']:
                rel = PurePosixPath(relative)
                if rel.is_absolute() or '..' in rel.parts:
                    raise ValueError('Unsafe manifest path')
                dest = staging.joinpath(*rel.parts)
                if dest.is_symlink() or not dest.resolve().is_relative_to(staging):
                    raise ValueError('Escaping or symlink destination')
                if dest.exists():
                    if not dest.is_file() or sha(dest.read_bytes()) != asset['payload_sha256']:
                        raise ValueError('Existing staging file differs; refusing overwrite: ' + relative)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with dest.open('xb') as output:
                        output.write(payload)
                hydrated.append(relative)
        receipt.append({'asset_id': asset['asset_id'], 'sha256': asset['payload_sha256'],
                        'bytes': len(payload), 'hydrated_paths': hydrated, 'verified': True})
    print(json.dumps({'schema': 'acceleratebench.data-hydration.v1', 'offline': args.offline,
                      'source_files_overwritten': False, 'assets': receipt}, indent=2))


if __name__ == '__main__':
    main()
