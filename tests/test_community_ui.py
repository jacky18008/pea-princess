"""Run browser-data-flow tests against the actual JavaScript, without a network."""
from pathlib import Path
import shutil
import subprocess
import unittest


class CommunityJavaScript(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is unavailable; Python privacy tests still run')
    def test_real_form_handlers_keep_private_notes_out_of_public_downloads(self):
        script = Path(__file__).with_suffix('.js')
        result = subprocess.run([shutil.which('node'), str(script)], capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn('functional checks passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
