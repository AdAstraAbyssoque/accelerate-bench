#!/usr/bin/env python3
"""Download the approved HF release and verify/install its exact canonical tasks."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify_and_install(archive, root, release, verify_only=False):
    manifest_path = root / 'canonical/manifest.json'
    manifest_bytes = manifest_path.read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != release['canonical_manifest_sha256']:
        raise ValueError('Canonical manifest differs from the release lock')
    manifest = json.loads(manifest_bytes)
    expected = {row['path']: row for row in manifest['files'] if row['included']}
    if len(expected) != sum(row['included'] for row in manifest['files']):
        raise ValueError('Duplicate source manifest entry')
    if archive.stat().st_size != release['bytes'] or digest_file(archive) != release['sha256']:
        raise ValueError('Archive size or SHA-256 mismatch; nothing installed')
    canonical = root / 'canonical'
    target = canonical / 'tasks'
    if canonical.is_symlink():
        raise ValueError('Canonical directory must not be a symlink')
    if not verify_only and (target.exists() or target.is_symlink()):
        raise FileExistsError('canonical/tasks already exists; preserve it and verify separately')
    required_bytes = sum(row['size_bytes'] for row in expected.values())
    if not verify_only and shutil.disk_usage(canonical).free < required_bytes + 64 * 1024**2:
        raise ValueError('Not enough free disk space for the verified task tree')
    staging = Path(tempfile.mkdtemp(prefix='.download-', dir=canonical)) if not verify_only else None
    seen, seen_paths, seen_dirs = set(), set(), set()
    embedded_manifest_verified = False
    try:
        with tarfile.open(archive, 'r|gz') as tar:
            for member in tar:
                path = PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts or not path.parts:
                    raise ValueError('Unsafe archive member path')
                name = str(path)
                if name in seen_paths:
                    raise ValueError('Duplicate archive member')
                seen_paths.add(name)
                if not (member.isfile() or member.isdir()):
                    raise ValueError('Archive links and special members are unsupported')
                if name == 'canonical/manifest.json':
                    if not member.isfile() or member.size != len(manifest_bytes):
                        raise ValueError('Embedded canonical manifest mismatch')
                    if tar.extractfile(member).read() != manifest_bytes:
                        raise ValueError('Embedded canonical manifest mismatch')
                    embedded_manifest_verified = True
                    continue
                if path.parts[:2] != ('canonical', 'tasks'):
                    continue
                relative = str(PurePosixPath(*path.parts[2:]))
                if relative == '.':
                    if not member.isdir():
                        raise ValueError('Expected task root directory')
                    continue
                if member.isdir():
                    if manifest['directory_modes'].get(relative) != member.mode:
                        raise ValueError('Unexpected directory or mode: ' + relative)
                    seen_dirs.add(relative)
                    if staging:
                        (staging / relative).mkdir(parents=True, exist_ok=True)
                    continue
                row = expected.get(relative)
                if row is None or member.size != row['size_bytes'] or member.mode != row['mode']:
                    raise ValueError('Unexpected source file, size or mode: ' + relative)
                dest = None
                try:
                    if staging:
                        out = staging / relative
                        out.parent.mkdir(parents=True, exist_ok=True)
                        dest = out.open('xb')
                    h = hashlib.sha256()
                    stream = tar.extractfile(member)
                    for block in iter(lambda: stream.read(1024 * 1024), b''):
                        h.update(block)
                        if dest:
                            dest.write(block)
                    if h.hexdigest() != row['sha256']:
                        raise ValueError('Source SHA-256 mismatch: ' + relative)
                finally:
                    if dest:
                        dest.close()
                if staging:
                    os.chmod(staging / relative, row['mode'])
                seen.add(relative)
        if not embedded_manifest_verified or seen != set(expected) or seen_dirs != set(manifest['directory_modes']):
            raise ValueError('Incomplete canonical source tree or manifest')
        if staging:
            # Atomic exclusive creation preserves even an empty directory created
            # concurrently. Link only already verified regular files, without
            # replacing destination entries. Both trees share the same filesystem.
            target.mkdir(mode=0o700)
            try:
                for name in sorted(manifest['directory_modes'], key=lambda value: (len(PurePosixPath(value).parts), value)):
                    (target / name).mkdir(mode=0o700)
                for name in sorted(expected):
                    os.link(staging / name, target / name)
                for name, mode in manifest['directory_modes'].items():
                    os.chmod(target / name, mode)
                os.chmod(target, 0o755)
            except Exception as exc:
                raise RuntimeError('Installation incomplete; partial canonical/tasks preserved for inspection') from exc
        return {'verified': True, 'installed': not verify_only, 'task_count': len(manifest['tasks']),
                'files': len(seen), 'external_hydration_required': manifest['external_hydration_paths'],
                'archive_sha256': release['sha256']}
    finally:
        if staging is not None:
            shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Use an already downloaded archive; no network')
    parser.add_argument('--revision', help='HF commit/tag override; exact content lock still applies')
    parser.add_argument('--verify-only', action='store_true', help='Verify every canonical byte/mode without installing')
    args = parser.parse_args()
    release = json.loads((ROOT / 'data-release.json').read_text())
    archive = args.archive
    if archive is None:
        from huggingface_hub import hf_hub_download
        archive = Path(hf_hub_download(repo_id=release['repo_id'], repo_type='dataset',
                                      filename=release['filename'], revision=args.revision or release['revision']))
    result = verify_and_install(archive, ROOT, release, args.verify_only)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
