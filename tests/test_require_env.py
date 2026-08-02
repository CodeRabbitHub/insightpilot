"""
Regression test for scripts/seed.py's require_env() helper: a missing
required env var must fail with a clear, actionable message (which var,
what to do), not a raw KeyError traceback. Flagged during this slice's
Gate 2 no-slop review as verified-by-hand-but-untested; this locks it in.
"""
import sys
import unittest

from _pg_helpers import REPO_ROOT

SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import seed  # noqa: E402


class RequireEnvTests(unittest.TestCase):
    def test_missing_env_var_raises_actionable_systemexit_not_keyerror(self):
        missing_var = "INSIGHTPILOT_TEST_VAR_DEFINITELY_UNSET"
        with self.assertRaises(SystemExit) as ctx:
            seed.require_env(missing_var)
        message = str(ctx.exception)
        self.assertIn(missing_var, message)
        self.assertIn(".env.example", message)


if __name__ == "__main__":
    unittest.main()
