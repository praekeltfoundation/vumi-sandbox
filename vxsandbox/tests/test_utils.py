"""Tests for vxsandbox.utils."""

import contextlib
import os

from twisted.trial.unittest import SkipTest

from vumi.tests.helpers import VumiTestCase

from vxsandbox.utils import SandboxError, find_nodejs_or_skip_test


class WorkerWithNodejs(object):
    @classmethod
    def find_nodejs(cls):
        return "/tmp/nodejs.worker.dummy"


class WorkerWithoutNodejs(object):
    @classmethod
    def find_nodejs(cls):
        return None


class TestSandboxError(VumiTestCase):
    def test_type(self):
        err = SandboxError("Eep")
        self.assertTrue(isinstance(err, Exception))

    def test_str(self):
        err = SandboxError("Eep")
        self.assertEqual(str(err), "Eep")


class TestFindNodejsOrSkipTest(VumiTestCase):
    def patch_vumi_test_node_path(self, path):
        def patched_get(name, default=None):
            if name == "VUMI_TEST_NODE_PATH":
                return path if path is not None else default
            return orig_env_get(name, default)
        orig_env_get = os.environ.get
        self.patch(os.environ, 'get', patched_get)

    def patch_os_path_isfile(self, path, value):
        def patched_isfile(filename):
            if filename == path:
                return value
            return orig_isfile(filename)
        orig_isfile = os.path.isfile
        self.patch(os.path, 'isfile', patched_isfile)

    @contextlib.contextmanager
    def fail_on_skip_test(self):
        try:
            yield
        except SkipTest:
            self.fail("SkipTest raised when node.js path expected")

    def test_valid_vumi_test_node_path(self):
        self.patch_vumi_test_node_path("/tmp/nodejs.env.dummy")
        self.patch_os_path_isfile("/tmp/nodejs.env.dummy", True)
        with self.fail_on_skip_test():
            self.assertEqual(
                find_nodejs_or_skip_test(WorkerWithoutNodejs),
                "/tmp/nodejs.env.dummy")

    def test_invalid_vumi_test_node_path(self):
        self.patch_vumi_test_node_path("/tmp/nodejs.env.dummy")
        self.patch_os_path_isfile("/tmp/nodejs.env.dummy", False)
        with self.fail_on_skip_test():
            err = self.failUnlessRaises(
                RuntimeError, find_nodejs_or_skip_test, WorkerWithoutNodejs)
            self.assertEqual(str(err), (
                "VUMI_TEST_NODE_PATH specified, but does not exist:"
                " /tmp/nodejs.env.dummy"))

    def test_worker_finds_nodejs(self):
        self.patch_vumi_test_node_path(None)
        with self.fail_on_skip_test():
            self.assertEqual(
                find_nodejs_or_skip_test(WorkerWithNodejs),
                "/tmp/nodejs.worker.dummy")

    def test_worker_doesnt_find_nodejs(self):
        self.patch_vumi_test_node_path(None)
        err = self.failUnlessRaises(
            SkipTest, find_nodejs_or_skip_test, WorkerWithoutNodejs)
        self.assertEqual(str(err), "No node.js executable found.")
