import unittest
from unittest.mock import patch, Mock
import tray_core as core

class Lifecycle(unittest.TestCase):
    def test_start_stop_key_session_and_environment(self):
        connection = core.Connection()
        proc = Mock()
        proc.running.return_value = True
        captured = []
        def fake_process(cmd, env, log):
            captured.append(dict(env))
            return proc
        with patch.object(core, 'matching_clients', return_value=[]), \
             patch.object(core.subprocess, 'run', return_value=Mock(returncode=0)), \
             patch.object(core, 'ManagedProcess', side_effect=fake_process), patch.object(core, 'ready_from_file', return_value=True):
            connection.start('sk-example-not-real')
            self.assertEqual(connection.state, 'on')
            self.assertEqual(captured[0]['CONTROL_PLANE_API_KEY'], 'sk-example-not-real')
            connection.stop()
            proc.close.assert_called_once()
            self.assertEqual(connection.state, 'off')
            self.assertEqual(connection.key, 'sk-example-not-real')
            connection.stop(clear_key=True)
            self.assertIsNone(connection.key)

    def test_invalid_auth_preserves_existing_connection(self):
        connection = core.Connection()
        with patch.object(core.subprocess, 'run', return_value=Mock(returncode=1)), \
             patch.object(core, 'matching_clients') as existing:
            with self.assertRaises(RuntimeError):
                connection.start('sk-example-not-real')
            existing.assert_not_called()
            self.assertEqual(connection.state, 'error')

    def test_detection_distinguishes_terminal_from_tray(self):
        connection = core.Connection()
        with patch.object(core, 'matching_clients', return_value=[123]):
            self.assertEqual(connection.detect(), 'external')
        with patch.object(core, 'matching_clients', return_value=[]):
            self.assertEqual(connection.detect(), 'off')

    def test_health_url_cannot_reach_remote_address(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        with TemporaryDirectory(dir=core.BASE) as folder:
            file = Path(folder) / 'health.txt'
            file.write_text('https://example.com')
            with patch.object(core.urllib.request, 'build_opener') as opener:
                self.assertFalse(core.ready_from_file(file))
                opener.assert_not_called()

if __name__ == '__main__':
    unittest.main()
