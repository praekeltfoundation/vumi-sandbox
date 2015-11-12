"""Tests for vxsandbox.rlimiter."""

import resource

from vumi.tests.helpers import VumiTestCase

from vxsandbox.rlimiter import SandboxRlimiter, ulimit_value


class TestSandboxRlimiter(VumiTestCase):
    """
    The actual spawning of the process is tested elsewhere.
    """

    def test_build_script(self):
        """
        The script contains a bunch of `ulimit` commands and an `exec`.
        """
        rlimiter = SandboxRlimiter({
            resource.RLIMIT_CPU: (40, 60),
            resource.RLIMIT_NOFILE: (15, 15),
        }, [])
        self.assertEqual(rlimiter.build_script(), "\n".join([
            "#!/bin/bash",
            "",
            "# Set resource limits.",
            "ulimit -St 40",
            "ulimit -Ht 60",
            "ulimit -Sn 15",
            "ulimit -Hn 15",
            "",
            'exec "$@"',
        ]))

    def test_build_script_negative_rlimit(self):
        """
        On some systems, -1 means "no limit".
        """
        uvalue = lambda v: v if v >= 0 else "unlimited"
        cpu_hard = uvalue(resource.getrlimit(resource.RLIMIT_CPU)[1])
        nofile_soft = uvalue(resource.getrlimit(resource.RLIMIT_NOFILE)[0])
        rlimiter = SandboxRlimiter({
            resource.RLIMIT_CPU: (40, -1),
            resource.RLIMIT_NOFILE: (-1, 15),
        }, [])
        self.assertEqual(rlimiter.build_script(), "\n".join([
            "#!/bin/bash",
            "",
            "# Set resource limits.",
            "ulimit -St 40",
            "ulimit -Ht %s" % (uvalue(cpu_hard),),
            "ulimit -Sn %s" % (uvalue(nofile_soft),),
            "ulimit -Hn 15",
            "",
            'exec "$@"',
        ]))

    def test_build_args(self):
        """
        The args contain a bash command to run the script we built.
        """
        rlimiter = SandboxRlimiter({
            resource.RLIMIT_CPU: (40, 60),
            resource.RLIMIT_NOFILE: (15, 15),
        }, ['/bin/echo', 'hello', 'world'])
        script = rlimiter.build_script()
        self.assertEqual(rlimiter.build_args(), [
            'bash', '-e', '-c', script, '--',
            '/bin/echo', 'hello', 'world'])

    def test_ulimit_value(self):
        """
        The ulimit value is the minimum of the new and current limits (if
        either exists) or "unlimited".
        """
        self.assertEqual(ulimit_value(-1, -1, 1), "unlimited")
        self.assertEqual(ulimit_value(0, -1, 1), 0)
        self.assertEqual(ulimit_value(-1, 0, 1), 0)
        self.assertEqual(ulimit_value(1, -1, 1), 1)
        self.assertEqual(ulimit_value(-1, 1, 1), 1)
        self.assertEqual(ulimit_value(0, 1, 1), 0)
        self.assertEqual(ulimit_value(1, 0, 1), 0)
        self.assertEqual(ulimit_value(3, 5, 1), 3)
        self.assertEqual(ulimit_value(5, 3, 1), 3)

    def test_ulimit_value_scaling(self):
        """
        The ulimit value is (if it exists) is scaled by the given factor.
        """
        self.assertEqual(ulimit_value(-1, -1, 4), "unlimited")
        self.assertEqual(ulimit_value(-1, 20, 4), 5)
        self.assertEqual(ulimit_value(20, -1, 4), 5)
        self.assertEqual(ulimit_value(-1, 21, 2), 10)
        self.assertEqual(ulimit_value(21, -1, 2), 10)
        self.assertEqual(ulimit_value(20, 21, 2), 10)
        self.assertEqual(ulimit_value(10, 25, 3), 3)
        self.assertEqual(ulimit_value(25, 10, 3), 3)
