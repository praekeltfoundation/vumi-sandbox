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

    # From the bash manual, regarding ulimit:
    # Values are in 1024-byte increments, except for -t, which is in seconds;
    # -p, which is in units of 512-byte blocks; and -T, -b, -n and -u, which
    # are unscaled values.
    ULIMIT_PARAMS = {
        resource.RLIMIT_CORE: ("c", 1024),
        resource.RLIMIT_CPU: ("t", 1),
        resource.RLIMIT_FSIZE: ("f", 1024),
        resource.RLIMIT_DATA: ("d", 1024),
        resource.RLIMIT_STACK: ("s", 1024),
        resource.RLIMIT_RSS: ("m", 1024),
        resource.RLIMIT_NOFILE: ("n", 1),
        resource.RLIMIT_MEMLOCK: ("l", 1024),
        resource.RLIMIT_AS: ("v", 1024),
    }

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
            param, scale = self.ULIMIT_PARAMS[rlimit]
            rsoft, rhard = resource.getrlimit(int(rlimit))
            yield "ulimit -S%s %s" % (param, ulimit_value(soft, rsoft, scale))
            yield "ulimit -H%s %s" % (param, ulimit_value(hard, rhard, scale))

    @classmethod
    def spawn(cls, reactor, protocol, rlimits, args, **kwargs):
        self = cls(rlimits, args, **kwargs)
        self.execute(reactor, protocol)


def ulimit_value(new, current, scale):
    if current >= 0 and (new < 0 or new > current):
        # The current limit is lower than the new one, so use that instead.
        return current / scale
    return new / scale if new >= 0 else "unlimited"
