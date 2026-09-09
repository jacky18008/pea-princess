"""Execute the actual UI event handlers offline, including uncertain HTTP responses."""
from pathlib import Path
import shutil
import subprocess
import unittest

class PlaygroundUI(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node unavailable; UI handler checks not run')
    def test_session_selection_idempotency_recovery_and_text_rendering(self):
        result=subprocess.run([shutil.which('node'),str(Path(__file__).with_suffix('.js'))],capture_output=True,text=True,timeout=20)
        self.assertEqual(0,result.returncode,result.stdout+result.stderr)
        self.assertIn('functional checks passed',result.stdout)
