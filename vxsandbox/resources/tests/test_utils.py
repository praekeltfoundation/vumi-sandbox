"""Tests for vxsandbox.resources.utils."""

import json

from vumi.tests.helpers import VumiTestCase
from vumi.message import MissingMessageField

from vxsandbox.resources.utils import (
    SandboxCommand, SandboxResources, SandboxResource)


class RecordingResource(SandboxResource):
    def __init__(self, *args, **kw):
        super(RecordingResource, self).__init__(*args, **kw)
        self.setup_calls = 0
        self.teardown_calls = 0

    def setup(self):
        self.setup_calls += 1

    def teardown(self):
        self.teardown_calls += 1


class TestSandboxCommand(VumiTestCase):
    def test_generate_id(self):
        cmd_id = SandboxCommand.generate_id()
        self.assertTrue(isinstance(cmd_id, basestring))
        self.assertEqual(len(cmd_id), 32)

    def test_defaults(self):
        class FixedIdCommand(SandboxCommand):
            generate_id = lambda self: '123'
        cmd = FixedIdCommand()
        self.assertEqual(cmd['cmd'], 'unknown')
        self.assertEqual(cmd['reply'], False)
        self.assertEqual(cmd['cmd_id'], '123')

    def test_from_json(self):
        cmd = SandboxCommand.from_json(json.dumps({
            'cmd_id': '123', 'cmd': 'name', 'reply': False,
        }))
        self.assertEqual(cmd, SandboxCommand(
            cmd_id='123', cmd='name', reply=False,
        ))

    def assert_field_missing(self, field, cmd_data):
        err = self.failUnlessRaises(
            MissingMessageField,
            SandboxCommand.from_json, json.dumps(cmd_data))
        self.assertEqual(str(err), field)

    def test_validate_cmd(self):
        self.assert_field_missing('cmd', {
            'cmd_id': '123', 'reply': False,
        })

    def test_validate_cmd_id(self):
        self.assert_field_missing('cmd_id', {
            'cmd': 'name', 'reply': False,
        })

    def test_validate_reply(self):
        self.assert_field_missing('reply', {
            'cmd_id': '123', 'cmd': 'name',
        })


class TestSandboxResources(VumiTestCase):
    def mk_resources(self, app_worker=None, config=None):
        app_worker = app_worker or object()
        config = config or {}
        return SandboxResources(app_worker, config)

    def class_name(self, cls):
        return '.'.join([cls.__module__, cls.__name__])

    def assert_recording_resource(
            self, resources, name, config={}, setup_calls=0, teardown_calls=0):
        resource = resources.resources[name]
        self.assertTrue(isinstance(resource, RecordingResource))
        self.assertEqual(resource.name, name)
        self.assertEqual(resource.app_worker, resources.app_worker)
        self.assertEqual(resource.config, config)
        self.assertEqual(resource.setup_calls, setup_calls)
        self.assertEqual(resource.teardown_calls, teardown_calls)

    def assert_recording_resources(self, resources, expected):
        for name, kw in expected.iteritems():
            self.assert_recording_resource(resources, name, **kw)
        self.assertEqual(set(resources.resources.keys()), set(expected.keys()))

    def test_create(self):
        dummy_worker = object()
        resources = SandboxResources(dummy_worker, {"conf": "foo"})
        self.assertEqual(resources.app_worker, dummy_worker)
        self.assertEqual(resources.config, {"conf": "foo"})
        self.assertEqual(resources.resources, {})

    def test_add_resource(self):
        resources = self.mk_resources()
        tst = RecordingResource("tst", resources.app_worker, {})
        self.assertEqual(resources.resources, {})
        resources.add_resource("tst", tst)
        self.assertEqual(resources.resources, {"tst": tst})
        self.assertEqual(tst.setup_calls, 0)
        self.assertEqual(tst.teardown_calls, 0)

    def test_validate_config(self):
        resources = self.mk_resources(config={
            'tst1': {
                'cls': self.class_name(RecordingResource),
            },
            'tst2': {
                'cls': self.class_name(RecordingResource),
                'extra': 'more config'
            },
        })
        self.assertEqual(resources.resources, {})
        resources.validate_config()
        self.assert_recording_resources(resources, {
            'tst1': {},
            'tst2': {'config': {'extra': 'more config'}}
        })

    def test_setup_resources(self):
        resources = self.mk_resources(config={
            'tst1': {'cls': self.class_name(RecordingResource)},
            'tst2': {'cls': self.class_name(RecordingResource)},
        })
        resources.validate_config()
        self.assert_recording_resources(resources, {
            'tst1': {'setup_calls': 0},
            'tst2': {'setup_calls': 0},
        })
        resources.setup_resources()
        self.assert_recording_resources(resources, {
            'tst1': {'setup_calls': 1},
            'tst2': {'setup_calls': 1},

        })

    def test_teardown_resources(self):
        resources = self.mk_resources(config={
            'tst1': {'cls': self.class_name(RecordingResource)},
            'tst2': {'cls': self.class_name(RecordingResource)},
        })
        resources.validate_config()
        self.assert_recording_resources(resources, {
            'tst1': {'teardown_calls': 0},
            'tst2': {'teardown_calls': 0},
        })
        resources.teardown_resources()
        self.assert_recording_resources(resources, {
            'tst1': {'teardown_calls': 1},
            'tst2': {'teardown_calls': 1},
        })


class TestSandboxResource(VumiTestCase):
    pass
