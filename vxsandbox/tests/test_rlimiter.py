"""Tests for vxsandbox.rlimiter."""

import resource

from vumi.tests.helpers import VumiTestCase

from vxsandbox.rlimiter import SandboxRlimiter


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
        cpu_hard = resource.getrlimit(resource.RLIMIT_CPU)[1]
        nofile_soft = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        rlimiter = SandboxRlimiter({
            resource.RLIMIT_CPU: (40, -1),
            resource.RLIMIT_NOFILE: (-1, 15),
        }, [])
        self.assertEqual(rlimiter.build_script(), "\n".join([
            "#!/bin/bash",
            "",
            "# Set resource limits.",
            "ulimit -St 40",
            "ulimit -Ht %s" % (cpu_hard,),
            "ulimit -Sn %s" % (nofile_soft,),
            "ulimit -Hn 15",
            "",
            'exec "$@"',
        ]))

    def test_build_script_no_RLIMIT_STACK(self):
        """
        We don't emit a `ulimit` command for RLIMIT_STACK because we're not
        allowed to set that.
        """
        rlimiter = SandboxRlimiter({
            resource.RLIMIT_CPU: (40, 60),
            resource.RLIMIT_NOFILE: (15, 15),
            resource.RLIMIT_STACK: (100, 100),
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
