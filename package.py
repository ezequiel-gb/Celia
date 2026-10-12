"""Build a source ZIP using an explicit allowlist and credential checks."""
import hashlib
from pathlib import Path
import re
import zipfile

BASE = Path(__file__).resolve().parent
FILES = ['README.md', 'TROUBLESHOOTING.md', 'SECURITY.md', 'PUBLISHING.md', 'VALIDATION.md',
         'INSTALLATION-A-TO-Z.md', 'PROJECT-EXPLAINED.md',
         '.gitignore', '.github/workflows/windows.yml', 'setup.py', 'package.py',
         'Install.cmd', 'Start-Celia.cmd']
FILES += ['service/' + name for name in ['engine.py', 'server.py', 'connect.py', 'tray_core.py',
          'tray.py', 'install_tray.py', 'review.py', 'test_service.py', 'test_tray.py',
          'requirements.txt', 'requirements.lock.txt', 'config.example.json']]
FILES += ['assets/celia-' + state + '.ico' for state in ['on', 'off', 'starting', 'error']]


def main():
    for name in FILES:
        file = BASE / name
        if not file.is_file() or not file.resolve().is_relative_to(BASE):
            raise ValueError('Missing or linked source file: ' + name)
        if file.suffix != '.ico':
            text = file.read_text('utf-8-sig')
            if re.search(r'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}', text):
                raise ValueError('Possible API secret in ' + name)
            ids = re.findall(r'tunnel_[a-z0-9]{32}', text)
            if any(value != 'tunnel_' + '0' * 32 for value in ids):
                raise ValueError('Account-specific tunnel in ' + name)
            if re.search(r'plugin_asdk_app_[a-z0-9]{20,}|org-[A-Za-z0-9]{16,}', text):
                raise ValueError('Possible account identifier in ' + name)
            if re.search(r'(?i)[a-z]:[/\\]+Users[/\\]+[^/\\\s]+', text):
                raise ValueError('Personal Windows profile path in ' + name)
    destination = BASE / 'dist'
    destination.mkdir(exist_ok=True)
    archive = destination / 'celia-files-source.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for name in FILES:
            output.write(BASE / name, 'celia-files/' + name)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (destination / 'SHA256SUMS.txt').write_text(digest + '  celia-files-source.zip\n', 'ascii')
    print(f'Checked and packaged {len(FILES)} allowlisted source files.')
    print(archive)
    print('SHA256: ' + digest)


if __name__ == '__main__':
    main()
