"""Privacy rejection and package tampering checks in disposable files."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json
from contextlib import redirect_stdout
import io
import zipfile
from package import scan,sources,verify,BASE
import upgrade

class PackageTests(unittest.TestCase):
    def test_privacy_patterns(self):
        samples=['sk-'+'x'*30,'tunnel_'+'a'*32,'plugin_asdk_app_'+'a'*24,
                 'C:/'+ 'Users/'+'Synthetic/private.txt','synthetic'+'@'+'example.invalid']
        for value in samples:
            with self.subTest(value=value[:10]):
                with self.assertRaises(ValueError):scan('fixture.md',value.encode())
        scan('fixture.md',('tunnel_'+'0'*32).encode())

    def test_tampered_package_rejected(self):
        data=sources()
        archive=BASE/'dist/celious-files-source.zip'
        verify(archive,data)
        with tempfile.TemporaryDirectory(prefix='celious-package-test-') as tmp:
            target=Path(tmp)/archive.name
            with zipfile.ZipFile(archive) as original,zipfile.ZipFile(target,'w') as altered:
                for name in original.namelist():
                    content=original.read(name)
                    if name.endswith('/README.md'):content+=b'\nTampered'
                    altered.writestr(name,content)
            (target.parent/'SHA256SUMS.txt').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name+'\n','ascii')
            with self.assertRaises(ValueError):verify(target,data)

    def test_overlay_failure_restores_originals_and_preserves_new_files(self):
        with tempfile.TemporaryDirectory(prefix='celious-overlay-test-') as tmp:
            root=Path(tmp);source=root/'source';live=root/'installed';backup=root/'backups'
            for p in [source/'service',live/'service',root/'projects',root/'vault']:p.mkdir(parents=True)
            for name in upgrade.MODULES:(source/'service'/name).write_bytes(b'new module')
            for name in upgrade.GUIDES:(source/name).write_bytes(b'new guide')
            (source/'service/requirements.lock.txt').write_bytes(b'same lock\r\n')
            (live/'service/requirements.lock.txt').write_bytes(b'same lock\n')
            for name in ['engine.py','server.py']:(live/'service'/name).write_bytes(b'old module')
            config=json.dumps(dict(roots=dict(Projects=dict(path=str(root/'projects')),Vault=dict(path=str(root/'vault'))))).encode()
            (live/'service/config.json').write_bytes(config)
            real_replace=upgrade.replace;count=0
            def interrupted(path,data):
                nonlocal count
                count+=1
                if count==4:raise OSError('Injected overlay interruption')
                real_replace(path,data)
            argv=['upgrade.py','--installation',str(live),'--backup-dir',str(backup),'--enable-memory','--apply','--connection-off']
            with patch.object(upgrade,'BASE',source),patch.object(upgrade,'replace',interrupted),patch('sys.argv',argv),redirect_stdout(io.StringIO()):
                with self.assertRaises(OSError):upgrade.main()
            self.assertEqual((live/'service/engine.py').read_bytes(),b'old module')
            self.assertEqual((live/'service/server.py').read_bytes(),b'old module')
            self.assertEqual((live/'service/config.json').read_bytes(),config)
            self.assertFalse((live/'service/second_brain.py').exists())
            self.assertEqual(len(list(backup.glob('*/failed-new-files/service/second_brain.py'))),1)

if __name__=='__main__':unittest.main(verbosity=2)
