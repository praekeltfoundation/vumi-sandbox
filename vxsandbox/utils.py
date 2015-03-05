# -*- test-case-name: vxsandbox.tests.test_utils -*-

import os

from twisted.trial.unittest import SkipTest


class SandboxError(Exception):
    """Raised when an error occurs inside the sandbox."""


def find_nodejs_or_skip_test(worker_class):
    """
    Find the node.js executable by checking the ``VUMI_TEST_NODE_PATH`` envvar
    and falling back to the provided worker's own detection method. If no
    executable is found, :class:`SkipTest` is raised.
    """
    path = os.environ.get('VUMI_TEST_NODE_PATH')
    if path is not None:
        if os.path.isfile(path):
            return path
        raise RuntimeError(
            "VUMI_TEST_NODE_PATH specified, but does not exist: %s" % (path,))

    path = worker_class.find_nodejs()
    if path is None:
        raise SkipTest("No node.js executable found.")
    return path
