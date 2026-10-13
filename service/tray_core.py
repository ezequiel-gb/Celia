"""Background connection lifecycle for the Celious tray application."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import pythoncom
import win32api
import win32com.client
import win32con
import win32job
import win32process
import win32event
import win32file
import pywintypes
from connect import BASE, CLIENT, PROFILES, TUNNEL_ID

RUNTIME = BASE / '.runtime'
HEALTH_FILE = RUNTIME / 'tray-health-url.txt'
NO_WINDOW = 0x08000000


def matching_clients():
    """Identify only this installed client and this tunnel, without reading secrets."""
    pythoncom.CoInitialize()
    try:
        wmi = win32com.client.GetObject('winmgmts:')
        found = []
        for p in wmi.ExecQuery("SELECT ProcessId, ExecutablePath, CommandLine FROM Win32_Process WHERE Name='tunnel-client.exe'"):
            if p.ExecutablePath and os.path.normcase(os.path.abspath(p.ExecutablePath)) == os.path.normcase(str(CLIENT)) and TUNNEL_ID in (p.CommandLine or ''):
                found.append(int(p.ProcessId))
        return found
    finally:
        pythoncom.CoUninitialize()


def ready_from_file(file):
    try:
        url = Path(file).read_text('utf-8').strip()
        # Never follow arbitrary endpoints supplied through runtime files.
        from urllib.parse import urlsplit
        parts = urlsplit(url)
        if parts.scheme != 'http' or parts.hostname != '127.0.0.1' or not parts.port or parts.path not in ('', '/'):
            return False
        req = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with req.open(url.rstrip('/') + '/readyz', timeout=1) as response:
            return response.status == 200 and response.read(64).strip() == b'ready'
    except (OSError, ValueError):
        return False


class ManagedProcess:
    """Start suspended, assign a kill-on-close Job Object, then run hidden."""
    def __init__(self, command, env, log):
        self.job = win32job.CreateJobObject(None, '')
        limits = win32job.QueryInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation)
        limits['BasicLimitInformation']['LimitFlags'] |= win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(self.job, win32job.JobObjectExtendedLimitInformation, limits)
        security = pywintypes.SECURITY_ATTRIBUTES()
        security.bInheritHandle = True
        output = win32file.CreateFile(str(log), win32con.GENERIC_WRITE, win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                                     security, win32con.OPEN_ALWAYS, win32con.FILE_ATTRIBUTE_NORMAL, None)
        win32file.SetFilePointer(output, 0, win32con.FILE_END)
        input_handle = win32file.CreateFile('NUL', win32con.GENERIC_READ, win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                                           security, win32con.OPEN_EXISTING, 0, None)
        startup = win32process.STARTUPINFO()
        startup.dwFlags = win32con.STARTF_USESTDHANDLES | win32con.STARTF_USESHOWWINDOW
        startup.wShowWindow = win32con.SW_HIDE
        startup.hStdInput = input_handle
        startup.hStdOutput = startup.hStdError = output
        process, thread, pid, _ = win32process.CreateProcess(None, subprocess.list2cmdline(command), None, None, True,
                                                            NO_WINDOW | win32con.CREATE_SUSPENDED, env, str(BASE), startup)
        self.handle, self.pid = process, pid
        try:
            win32job.AssignProcessToJobObject(self.job, process)
            win32process.ResumeThread(thread)
        except Exception:
            win32process.TerminateProcess(process, 1)
            self.close()
            raise
        finally:
            thread.Close()
            output.Close()
            input_handle.Close()

    def running(self):
        return self.handle is not None and win32process.GetExitCodeProcess(self.handle) == win32con.STILL_ACTIVE

    def close(self):
        if self.job is not None:
            win32job.TerminateJobObject(self.job, 0)
            self.job.Close()
            self.job = None
        if self.handle is not None:
            win32event.WaitForSingleObject(self.handle, 5000)
            self.handle.Close()
            self.handle = None


class Connection:
    def __init__(self):
        self.process = None
        self.key = None
        self.state = 'off'
        self.message = 'Celious is off'
        self.external = []

    def detect(self):
        self.external = matching_clients() if not self.process else []
        if self.process and self.process.running():
            self.state = 'on' if ready_from_file(HEALTH_FILE) else 'starting'
            self.message = 'Connected in the background' if self.state == 'on' else 'Connecting…'
        elif self.external:
            self.state = 'external'
            self.message = 'Running in the old terminal — move it to the tray'
        else:
            if self.process:
                self.process.close()
                self.process = None
                self.state = 'error'
                self.message = 'Connection stopped unexpectedly. Open the connection log.'
            elif self.state not in ('error', 'starting'):
                self.state, self.message = 'off', 'Celious is off'
        return self.state

    def start(self, key):
        # Avoid loading the full MCP SDK on a GUI worker thread. Doctor checks the server itself.
        for required in [CLIENT, PROFILES / 'celious.yaml', BASE / 'server.py']:
            if not required.is_file():
                raise FileNotFoundError('Celious setup file missing: ' + required.name)
        env = os.environ.copy()
        env['CONTROL_PLANE_API_KEY'] = key
        self.state, self.message = 'starting', 'Checking the connection…'
        common = ['--profile', 'celious', '--profile-dir', str(PROFILES), '--control-plane.tunnel-id', TUNNEL_ID]
        try:
            with (RUNTIME / 'tray-connection.log').open('ab') as log:
                result = subprocess.run([str(CLIENT), 'doctor', *common, '--explain'], env=env,
                                        stdout=log, stderr=log, creationflags=NO_WINDOW, timeout=60, shell=False)
            if result.returncode:
                raise RuntimeError('Connection check failed. Open the connection log for details.')
            self.stop(clear_key=False)
            HEALTH_FILE.unlink(missing_ok=True)
            self.process = ManagedProcess([str(CLIENT), 'run', *common, '--health.url-file', str(HEALTH_FILE),
                                           '--mcp.stdio-send-initialized-notification'], env, RUNTIME / 'tray-connection.log')
            self.key = key
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and self.process.running():
                if ready_from_file(HEALTH_FILE):
                    self.state, self.message = 'on', 'Connected in the background'
                    return
                time.sleep(0.25)
            raise RuntimeError('Connection did not become ready. Open the connection log.')
        except Exception:
            if self.process:
                self.process.close()
                self.process = None
            self.state = 'error'
            raise
        finally:
            env.pop('CONTROL_PLANE_API_KEY', None)

    def stop(self, clear_key=False):
        if self.process:
            self.process.close()
            self.process = None
        # Recheck identity immediately before stopping any adopted terminal connection.
        for pid in matching_clients():
            subprocess.run(['taskkill.exe', '/PID', str(pid), '/T', '/F'], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, creationflags=NO_WINDOW, shell=False, check=True)
        self.external = []
        if clear_key:
            self.key = None
        self.state, self.message = 'off', 'Celious is off'
