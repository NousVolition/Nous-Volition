"""Regression checks for lossless restoration and refusal of incomplete archives."""
import copy
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import restore_numerical_data as data


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root/'assets'
        self.assets.mkdir()
        self.dest = self.root/'checkout'
        self.cache = self.root/'cache'
        self.payloads = {'reports/a/data.npz': b'original numerical bytes\x00\x01',
                         'reports/b/parts.part00': b'part zero',
                         'README.md': b'# original report\n'}
        self.catalog = {'schema': 1, 'repository': 'Example/Study',
                        'release_tag': 'data-v1', 'files': [], 'assets': []}
        for i, (path, content) in enumerate(self.payloads.items()):
            name = str(i) + '.zip'
            with zipfile.ZipFile(self.assets/name, 'w') as out:
                out.writestr(path, content)
            self.catalog['files'].append({'path': path, 'bytes': len(content),
                'sha256': hashlib.sha256(content).hexdigest(), 'asset': name,
                'kind': 'source' if path == 'README.md' else 'numerical'})
            self.catalog['assets'].append({'name': name, 'files': 1,
                'url': 'https://github.com/Example/Study/releases/download/data-v1/' + name})
            self.rehash(i)
        self.catalog_path = self.root/'catalog.json'

    def rehash(self, i):
        asset = self.catalog['assets'][i]
        path = self.assets/asset['name']
        asset.update(bytes=path.stat().st_size, sha256=data.digest(path))

    def load(self):
        self.catalog_path.write_text(json.dumps(self.catalog), encoding='utf-8')
        return data.load_catalog(self.catalog_path)

    def restore(self, **kwargs):
        return data.restore(self.load(), self.dest, self.cache, self.assets, **kwargs)

    def test_full_restore_exact_and_idempotent(self):
        self.assertEqual(self.restore(full=True)['written_files'], 3)
        for name, payload in self.payloads.items():
            self.assertEqual((self.dest/name).read_bytes(), payload)
        self.assertEqual(self.restore(full=True)['written_files'], 0)
        self.assertEqual(data.verify_files(self.load(), self.dest, full=True), 3)

    def test_numerical_only_and_study_selection(self):
        self.assertEqual(self.restore(studies=['reports/a'])['selected_files'], 1)
        self.assertFalse((self.dest/'reports/b').exists())
        self.assertEqual(self.restore()['selected_files'], 2)
        self.assertFalse((self.dest/'README.md').exists())
        with self.assertRaisesRegex(ValueError, 'No catalog files'):
            self.restore(studies=['absent'])

    def test_missing_later_archive_writes_nothing(self):
        (self.assets/'1.zip').unlink()
        with self.assertRaises(FileNotFoundError):
            self.restore()
        self.assertFalse(self.dest.exists())

    def test_corrupt_outer_archive_is_rejected(self):
        with (self.assets/'1.zip').open('ab') as out:
            out.write(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'Archive checksum'):
            self.restore()
        self.assertFalse(self.dest.exists())

    def test_changed_member_with_matching_outer_hash_is_rejected(self):
        path = 'reports/b/parts.part00'
        with zipfile.ZipFile(self.assets/'1.zip', 'w') as out:
            out.writestr(path, b'evil zero')
        self.rehash(1)
        with self.assertRaisesRegex(ValueError, 'Member checksum'):
            self.restore()
        self.assertFalse(self.dest.exists())

    def test_missing_extra_and_duplicate_members(self):
        for mode in ('missing', 'extra', 'duplicate'):
            with self.subTest(mode=mode):
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    with zipfile.ZipFile(self.assets/'1.zip', 'w') as out:
                        if mode != 'missing':
                            name = 'reports/b/parts.part00'
                            out.writestr(name, self.payloads[name])
                            out.writestr('extra' if mode == 'extra' else name, b'x')
                self.rehash(1)
                with self.assertRaisesRegex(ValueError, 'member inventory'):
                    self.restore()
                self.assertFalse(self.dest.exists())

    def test_existing_changed_file_is_never_overwritten(self):
        target = self.dest/'reports/b/parts.part00'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'user work')
        with self.assertRaisesRegex(ValueError, 'Refusing to overwrite'):
            self.restore()
        self.assertEqual(target.read_bytes(), b'user work')
        self.assertFalse((self.dest/'reports/a').exists())

    def test_unsafe_and_duplicate_catalog_paths(self):
        original = copy.deepcopy(self.catalog)
        for name in ('../outside', '/absolute', 'a/../b', 'a\\b', 'C:/bad', 'a//b'):
            self.catalog = copy.deepcopy(original)
            self.catalog['files'][0]['path'] = name
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.load()
        self.catalog = copy.deepcopy(original)
        self.catalog['files'].append(self.catalog['files'][0])
        with self.assertRaisesRegex(ValueError, 'Duplicate file'):
            self.load()

    def test_symlink_archive_member_rejected(self):
        name = 'reports/b/parts.part00'
        info = zipfile.ZipInfo(name)
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(self.assets/'1.zip', 'w') as out:
            out.writestr(info, self.payloads[name])
        self.rehash(1)
        with self.assertRaisesRegex(ValueError, 'Invalid archive member'):
            self.restore()

    def test_catalog_rejects_wrong_release_and_count(self):
        self.catalog['assets'][0]['url'] = 'https://example.com/elsewhere'
        with self.assertRaisesRegex(ValueError, 'Asset URL'):
            self.load()
        self.catalog['assets'][0]['files'] = 2
        with self.assertRaisesRegex(ValueError, 'file count'):
            self.load()

    def test_verification_rejects_missing_or_changed_restored_file(self):
        self.restore()
        target = self.dest/'reports/a/data.npz'
        target.write_bytes(b'different')
        with self.assertRaisesRegex(ValueError, 'Missing or changed'):
            data.verify_files(self.load(), self.dest)
        target.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing or changed'):
            data.verify_files(self.load(), self.dest)

    def test_download_checks_bytes_and_removes_failed_partial(self):
        asset = self.catalog['assets'][0]
        with mock.patch.object(data.urllib.request, 'urlopen', return_value=io.BytesIO(b'bad response')):
            with self.assertRaisesRegex(ValueError, 'Downloaded archive checksum'):
                data.obtain(asset, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])
        with mock.patch.object(data.urllib.request, 'urlopen', return_value=io.BytesIO((self.assets/'0.zip').read_bytes())):
            downloaded = data.obtain(asset, self.cache)
        self.assertTrue(data.matching(downloaded, asset))
        # A damaged cached archive must not be accepted on later offline use.
        downloaded.write_bytes(b'changed cache')
        with self.assertRaisesRegex(ValueError, 'Archive checksum'):
            data.obtain(asset, self.cache)

    def test_checker_verifies_untracked_restored_data(self):
        # This case runs once the tool is installed beside the repository checker.
        checker_file = Path(__file__).with_name('check_repository.py')
        if not checker_file.exists():
            self.skipTest('repository integration runs in the prepared checkout')
        import check_repository
        self.restore()
        (self.dest/'data-release').mkdir()
        (self.dest/'data-release/catalog.json').write_text(json.dumps(self.catalog), encoding='utf-8')
        (self.dest/'README.md').write_text('[Data](reports/a/data.npz)\n', encoding='utf-8')
        (self.dest/'.git').mkdir()
        tracked = b'README.md\0data-release/catalog.json\0'
        with mock.patch.object(check_repository.subprocess, 'check_output', return_value=tracked):
            counts, errors = check_repository.check(self.dest)
            self.assertFalse(errors)
            self.assertEqual(counts['restored_numerical_files'], 2)
            (self.dest/'reports/a/data.npz').unlink()
            counts, errors = check_repository.check(self.dest)
            self.assertTrue(any('Release data missing or changed' in e for e in errors))
            self.assertTrue(any('missing link target' in e for e in errors))
if __name__ == '__main__':
    unittest.main()
