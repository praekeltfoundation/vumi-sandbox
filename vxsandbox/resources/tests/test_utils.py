"""Tests for vxsandbox.resources.utils."""

import json
import logging

from twisted.internet.defer import Deferred

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


class RecordingApi(object):
    def __init__(self, sandbox_id='sandbox_uno'):
        self.sandbox_id = sandbox_id
        self.logs = []
        self.deaths = 0

    def log(self, msg, lvl):
        self.logs.append((msg, lvl))

    def sandbox_kill(self):
        self.deaths += 1


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

    def assert_recording_resource(self, resources, name, config=None,
                                  setup_calls=0, teardown_calls=0):
        config = config or {}
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


class CommandHandler(object):
    def __init__(self, name, test_case, result=None):
        self._name = name
        self._test_case = test_case
        self._calls = []
        self._result = result or object()

    def assert_called(self, api, cmd, result_d):
        self._test_case.assertEqual(self._calls, [(api, cmd)])
        if isinstance(self._result, Deferred):
            self._test_case.assertEqual(result_d, self._result)
        else:
            self._test_case.assertTrue(result_d.called)
            self._test_case.assertEqual(result_d.result, self._result)

    def __call__(self, api, cmd):
        self._calls.append((api, cmd))
        return self._result


class TestSandboxResource(VumiTestCase):
    def mk_resource(self, name, app_worker=None, config=None, handler=None):
        app_worker = app_worker or object()
        config = config or {}
        resource = SandboxResource(name, app_worker, config)
        if handler is not None:
            setattr(resource, handler._name, handler)
        return resource

    def assert_recording_api(self, api, logs=None, deaths=0):
        logs = logs or []
        self.assertEqual(api.logs, logs)
        self.assertEqual(api.deaths, deaths)

    def test_create(self):
        dummy_worker = object()
        resource = SandboxResource(
            'noir', dummy_worker, {'colour': 'black'})
        self.assertEqual(resource.name, 'noir')
        self.assertEqual(resource.app_worker, dummy_worker)
        self.assertEqual(resource.config, {'colour': 'black'})

    def test_setup(self):
        resource = self.mk_resource('test')
        resource.setup()

    def test_teardown(self):
        resource = self.mk_resource('test')
        resource.teardown()

    def test_sandbox_init(self):
        api = RecordingApi()
        resource = self.mk_resource('test')
        resource.sandbox_init(api)
        self.assert_recording_api(api, logs=[])

    def test_reply(self):
        resource = self.mk_resource('test')
        cmd = SandboxCommand(cmd='dothing', cmd_id='123')
        reply = resource.reply(cmd, thing='done')
        self.assertEqual(reply, SandboxCommand(
            cmd='dothing', cmd_id='123', reply=True, thing='done',
        ))

    def test_reply_error(self):
        resource = self.mk_resource('test')
        cmd = SandboxCommand(cmd='dothing', cmd_id='123')
        error = resource.reply_error(cmd, 'failed-to-do-thing')
        self.assertEqual(error, SandboxCommand(
            cmd='dothing', cmd_id='123', reply=True,
            success=False, reason='failed-to-do-thing',
        ))

    def test_dispatch_known_request(self):
        handler = CommandHandler('handle_dothing', self)
        resource = self.mk_resource('test', handler=handler)
        api = RecordingApi()
        cmd = SandboxCommand(cmd='dothing', arg=1)
        d = resource.dispatch_request(api, cmd)
        handler.assert_called(api, cmd, d)

    def test_dispatch_unknown_request(self):
        handler = CommandHandler('unknown_request', self)
        resource = self.mk_resource('test', handler=handler)
        api = RecordingApi()
        cmd = SandboxCommand(cmd='do_unknown_thing', arg=1)
        d = resource.dispatch_request(api, cmd)
        handler.assert_called(api, cmd, d)

    def test_dispatch_deferred_request(self):
        handler = CommandHandler(
            'handle_deferred', self, result=Deferred())
        resource = self.mk_resource('test', handler=handler)
        api = RecordingApi()
        cmd = SandboxCommand(cmd='deferred', arg=1)
        d = resource.dispatch_request(api, cmd)
        handler.assert_called(api, cmd, d)

    def test_unknown_request(self):
        api = RecordingApi()
        cmd = SandboxCommand(cmd='dothing', arg=1)

        resource = self.mk_resource('test')
        result = resource.unknown_request(api, cmd)

        self.assertEqual(result, None)
        [[msg, lvl]] = api.logs
        self.assertTrue(msg.startswith(
            "Resource test received unknown command 'dothing' from sandbox"
            " 'sandbox_uno'. Killing sandbox. [Full command:"
            " <Message payload="))
        self.assertEqual(lvl, logging.ERROR)
