import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

VERIFY = Path(__file__).resolve().parents[1] / 'scripts/verify.py'


class ClientReleaseTests(unittest.TestCase):
    def fixture(self, root, invalid_path=False):
        archive = root / 'hitry-slon.mrpack'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('modrinth.index.json', json.dumps({'versionId': '0.1.42-preview',
                'dependencies': {'minecraft': '1.21.1', 'neoforge': '21.1.266'},
                'files': [{'path': 'mods/example.jar', 'env': {'client': 'required'},
                           'hashes': {'sha512': 'a' * 128}, 'downloads': ['https://cdn.modrinth.com/example.jar']}]}))
            if invalid_path:z.writestr('config/server.properties', 'private')
        meta = {'tag': 'v0.1.42-preview', 'source_commit': 'a' * 40, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'minecraft': '1.21.1', 'neoforge': '21.1.266', 'prerelease': True}
        (root / 'release.json').write_text(json.dumps(meta))
        return meta

    def verify(self, root):
        return subprocess.run(['python3', str(VERIFY), '--release-dir', str(root)], capture_output=True, text=True)

    def test_valid_preview_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);self.fixture(root)
            self.assertEqual(self.verify(root).returncode, 0)

    def test_altered_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);self.fixture(root)
            (root / 'hitry-slon.mrpack').write_bytes(b'altered')
            self.assertNotEqual(self.verify(root).returncode, 0)

    def test_private_server_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);self.fixture(root, invalid_path=True)
            self.assertNotEqual(self.verify(root).returncode, 0)

    def test_wrong_channel_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);meta=self.fixture(root);meta['prerelease']=False
            (root / 'release.json').write_text(json.dumps(meta))
            self.assertNotEqual(self.verify(root).returncode, 0)


if __name__ == '__main__':
    unittest.main()
