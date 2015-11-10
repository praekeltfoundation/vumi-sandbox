# -*- test-case-name: vxsandbox.tests.test_sandbox_rlimiter -*-

"""
A helper for applying RLIMITS to a sandboxed process.
"""

import resource


class SandboxRlimiter(object):
    """
    Spawn a process that applies rlimits and then execs another program.

    It's necessary because Twisted's spawnProcess has no equivalent of
    the `preexec_fn` argument to :class:`subprocess.POpen`.

    See http://twistedmatrix.com/trac/ticket/4159.
    """

    ULIMIT_PARAMS = {
        resource.RLIMIT_CORE: "c",
        resource.RLIMIT_CPU: "t",
        resource.RLIMIT_FSIZE: "f",
        resource.RLIMIT_DATA: "d",
        resource.RLIMIT_STACK: "s",
        resource.RLIMIT_RSS: "m",
        resource.RLIMIT_NOFILE: "n",
        resource.RLIMIT_MEMLOCK: "l",
        resource.RLIMIT_AS: "v",
    }

    # These ones can't always be set, so ignore them.
    ULIMIT_SKIP = (
        resource.RLIMIT_STACK,
        resource.RLIMIT_MEMLOCK,
    )

    def __init__(self, rlimits, args, **kwargs):
        self._args = args
        self._rlimits = rlimits
        self._kwargs = kwargs

    def execute(self, reactor, protocol):
        reactor.spawnProcess(
            protocol, '/bin/bash', args=self.build_args(), **self._kwargs)

    def build_args(self):
        return ['bash', '-e', '-c', self.build_script(), '--'] + self._args

    def build_script(self):
        script_lines = ["#!/bin/bash", ""]
        script_lines.extend(self._build_rlimit_commands())
        script_lines.extend(["", 'exec "$@"'])
        return "\n".join(script_lines)

    def _build_rlimit_commands(self):
        yield "# Set resource limits."
        for rlimit, (soft, hard) in sorted(self._rlimits.items()):
            if rlimit in self.ULIMIT_SKIP:
                # We can't set this one.
                continue
            param = self.ULIMIT_PARAMS[rlimit]
            rsoft, rhard = resource.getrlimit(int(rlimit))
            yield "ulimit -S%s %s" % (param, minpositive(soft, rsoft))
            yield "ulimit -H%s %s" % (param, minpositive(hard, rhard))

    @classmethod
    def spawn(cls, reactor, protocol, rlimits, args, **kwargs):
        self = cls(rlimits, args, **kwargs)
        self.execute(reactor, protocol)


def minpositive(a, b):
    if a < 0:
        return b
    if b < 0:
        return a
    return min(a, b)
