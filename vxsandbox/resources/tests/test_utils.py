"""Tests for vxsandbox.resources.utils."""

import json

from vumi.tests.helpers import VumiTestCase
from vumi.message import MissingMessageField

from vxsandbox.resources.utils import (
    SandboxCommand, SandboxResources, SandboxResource)


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
    pass


class TestSandboxResource(VumiTestCase):
    pass
