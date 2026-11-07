import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('download_data', Path(__file__).resolve().parents[1] / 'scripts/download_data.py')
DOWNLOAD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOWNLOAD)


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'canonical').mkdir()
        self.payload = b'#!/bin/sh\nexit 0\n'
        self.manifest = {'tasks': ['sample'], 'files': [
            {'path': 'sample/run.sh', 'included': True, 'mode': 0o755,
             'size_bytes': len(self.payload), 'sha256': hashlib.sha256(self.payload).hexdigest()},
            {'path': 'sample/external.bin', 'included': False, 'mode': 0o644,
             'size_bytes': 99, 'sha256': 'f' * 64}],
            'directory_modes': {'sample': 0o755}, 'external_hydration_paths': ['sample/external.bin']}
        self.manifest_bytes = json.dumps(self.manifest).encode()
        (self.root / 'canonical/manifest.json').write_bytes(self.manifest_bytes)

    def archive(self, *, payload=None, omit=False, extra=None, mode=0o755, embedded=None):
        archive = self.root / 'fixture.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            def file(name, content, filemode=0o644):
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(content), filemode
                tar.addfile(info, io.BytesIO(content))
            file('canonical/manifest.json', self.manifest_bytes if embedded is None else embedded)
            directory = tarfile.TarInfo('canonical/tasks/sample')
            directory.type, directory.mode = tarfile.DIRTYPE, 0o755
            tar.addfile(directory)
            if not omit:
                file('canonical/tasks/sample/run.sh', self.payload if payload is None else payload, mode)
            if extra:
                name, kind = extra
                if kind == 'link':
                    info = tarfile.TarInfo(name)
                    info.type, info.linkname = tarfile.SYMTYPE, '../../outside'
                    tar.addfile(info)
                else:
                    file(name, b'bad')
        release = {'bytes': archive.stat().st_size, 'sha256': DOWNLOAD.digest_file(archive),
                   'canonical_manifest_sha256': hashlib.sha256(self.manifest_bytes).hexdigest()}
        return archive, release

    def reject(self, archive, release):
        with self.assertRaises((ValueError, FileExistsError)):
            DOWNLOAD.verify_and_install(archive, self.root, release)
        self.assertFalse((self.root / 'canonical/tasks').exists())
        self.assertEqual(list((self.root / 'canonical').glob('.download-*')), [])

    def test_install_exact_bytes_and_executable_mode(self):
        archive, release = self.archive()
        result = DOWNLOAD.verify_and_install(archive, self.root, release)
        self.assertTrue(result['installed'])
        target = self.root / 'canonical/tasks/sample/run.sh'
        self.assertEqual(target.read_bytes(), self.payload)
        self.assertEqual(target.stat().st_mode & 0o7777, 0o755)
        self.assertFalse((target.parent / 'external.bin').exists())

    def test_verify_only_never_installs(self):
        archive, release = self.archive()
        self.assertFalse(DOWNLOAD.verify_and_install(archive, self.root, release, True)['installed'])
        self.assertFalse((self.root / 'canonical/tasks').exists())

    def test_existing_tree_is_preserved(self):
        archive, release = self.archive()
        (self.root / 'canonical/tasks').mkdir()
        keep = self.root / 'canonical/tasks/user-work.txt'
        keep.write_text('preserve')
        with self.assertRaises(FileExistsError):
            DOWNLOAD.verify_and_install(archive, self.root, release)
        self.assertEqual(keep.read_text(), 'preserve')

    def test_concurrently_created_empty_tree_is_preserved(self):
        archive, release = self.archive()
        target = self.root / 'canonical/tasks'
        original = Path.mkdir
        def race(path, *args, **kwargs):
            if path == target and not target.exists():
                original(target, mode=0o700)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'mkdir', race), self.assertRaises(FileExistsError):
            DOWNLOAD.verify_and_install(archive, self.root, release)
        self.assertEqual(target.stat().st_mode & 0o7777, 0o700)
        self.assertEqual(list(target.iterdir()), [])
        self.assertEqual(list((self.root / 'canonical').glob('.download-*')), [])

    def test_publication_failure_preserves_partial_tree(self):
        archive, release = self.archive()
        with patch.object(DOWNLOAD.os, 'link', side_effect=OSError('fixture')), self.assertRaisesRegex(RuntimeError, 'partial'):
            DOWNLOAD.verify_and_install(archive, self.root, release)
        self.assertTrue((self.root / 'canonical/tasks/sample').is_dir())
        self.assertFalse((self.root / 'canonical/tasks/sample/run.sh').exists())
        self.assertEqual(list((self.root / 'canonical').glob('.download-*')), [])

    def test_archive_digest_rejected_before_install(self):
        archive, release = self.archive()
        release['sha256'] = '0' * 64
        self.reject(archive, release)

    def test_corrupt_canonical_content_is_rejected(self):
        self.reject(*self.archive(payload=b'x' * len(self.payload)))

    def test_missing_canonical_file_is_rejected(self):
        self.reject(*self.archive(omit=True))

    def test_extra_canonical_file_is_rejected(self):
        self.reject(*self.archive(extra=('canonical/tasks/sample/extra', 'file')))

    def test_duplicate_member_is_rejected(self):
        self.reject(*self.archive(extra=('canonical/tasks/sample/run.sh', 'file')))

    def test_path_traversal_is_rejected(self):
        self.reject(*self.archive(extra=('canonical/tasks/sample/../../outside', 'file')))
        self.assertFalse((self.root / 'outside').exists())

    def test_symlink_is_rejected(self):
        self.reject(*self.archive(extra=('canonical/tasks/sample/link', 'link')))

    def test_mode_drift_is_rejected(self):
        self.reject(*self.archive(mode=0o644))

    def test_embedded_manifest_drift_is_rejected(self):
        self.reject(*self.archive(embedded=b'{}'))


if __name__ == '__main__':
    unittest.main()
