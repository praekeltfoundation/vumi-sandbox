"""Tests for vxsandbox.rlimiter."""

from vumi.tests.helpers import VumiTestCase

from vxsandbox import rlimiter
from vxsandbox.rlimiter import SandboxRlimiter


class TestSandboxRlimiter(VumiTestCase):
    def test_script_name_dot_py(self):
        self.patch(rlimiter, '__file__', 'foo.py')
        self.assertEqual(SandboxRlimiter.script_name(), 'foo.py')

    def test_script_name_dot_pyc(self):
        self.patch(rlimiter, '__file__', 'foo.pyc')
        self.assertEqual(SandboxRlimiter.script_name(), 'foo.py')

    def test_script_name_dot_pyo(self):
        self.patch(rlimiter, '__file__', 'foo.pyo')
        self.assertEqual(SandboxRlimiter.script_name(), 'foo.py')
