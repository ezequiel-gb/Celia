"""Install shortcuts for the Celious tray, without enabling the connection at login."""
import argparse
from pathlib import Path
import subprocess
import sys
import win32com.client
from win32com.shell import shell, shellcon
from connect import BASE

def shortcut(path, show=False):
    app = win32com.client.Dispatch('WScript.Shell')
    link = app.CreateShortcut(str(path))
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    if path.exists() and link.TargetPath and Path(link.TargetPath).resolve() != pythonw.resolve():
        raise FileExistsError('An unrelated shortcut already uses the Celious Switch name')
    link.TargetPath = str(pythonw)
    link.Arguments = subprocess.list2cmdline([str(BASE / 'tray.py')] + (['--show'] if show else []))
    link.WorkingDirectory = str(BASE)
    link.IconLocation = str(BASE.parent / 'assets' / 'celious-on.ico')
    link.Description = 'Celious connection switch — starts off, no terminal required'
    link.Save()
    return path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--startup', action='store_true', help='Show the tray icon at Windows login, with connection off')
    args = parser.parse_args()
    paths = [BASE.parent / 'Celious Switch.lnk', Path(shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, 0, 0)) / 'Celious Switch.lnk']
    for path in paths:
        print(shortcut(path, show=True))
    if args.startup:
        folder = Path(shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, 0, 0))
        print(shortcut(folder / 'Celious Switch.lnk'))
