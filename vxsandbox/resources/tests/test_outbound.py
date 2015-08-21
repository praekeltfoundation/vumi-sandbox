from twisted.internet.defer import succeed, inlineCallbacks

from vxsandbox.resources.outbound import OutboundResource
from vxsandbox.resources.tests.utils import ResourceTestCaseBase
from vxsandbox.tests.utils import DummyAppWorker


class StubbedAppWorker(DummyAppWorker):

    class DummyApi(DummyAppWorker.DummyApi):
        def __init__(self, inbound_messages):
            self._inbound_messages = inbound_messages

        def get_inbound_message(self, msg_id):
            return self._inbound_messages.get(msg_id)

    sandbox_api_cls = DummyApi

    def __init__(self):
        super(StubbedAppWorker, self).__init__()
        self._inbound_messages = {}

    def create_sandbox_api(self):
        return self.sandbox_api_cls(self._inbound_messages)

    def add_inbound_message(self, msg):
        self._inbound_messages[msg['message_id']] = msg


class TestOutboundResource(ResourceTestCaseBase):

    app_worker_cls = StubbedAppWorker
    resource_cls = OutboundResource

    @inlineCallbacks
    def setUp(self):
        super(TestOutboundResource, self).setUp()
        yield self.create_resource({})
        self.app_worker.add_inbound_message({u'message_id': u'known-id'})

    @inlineCallbacks
    def assert_cmd_fails(self, reason, cmd, resource_config=None, **cmd_args):
        yield self.create_resource(resource_config or {})
        reply = yield self.dispatch_command(cmd, **cmd_args)
        self.check_reply(reply, success=False, reason=reason)
        self.assertFalse(self.app_worker.mock_calls['send_to'], [])
        self.assertFalse(self.app_worker.mock_calls['reply_to'], [])
        self.assertFalse(self.app_worker.mock_calls['reply_to_group'], [])

    @inlineCallbacks
    def test_handle_reply_to(self):
        self.app_worker.mock_returns['reply_to'] = succeed(None)
        self.api.get_inbound_message = lambda msg_id: msg_id
        reply = yield self.dispatch_command('reply_to', content='hello',
                                            continue_session=True,
                                            in_reply_to='msg1')
        self.check_reply(reply, success=True)
        self.assertEqual(self.app_worker.mock_calls['reply_to'], [
            (('msg1', 'hello'), {
                'continue_session': True, 'helper_metadata': {}
            }),
        ])

    @inlineCallbacks
    def test_handle_reply_to_group(self):
        self.app_worker.mock_returns['reply_to_group'] = succeed(None)
        self.api.get_inbound_message = lambda msg_id: msg_id
        reply = yield self.dispatch_command('reply_to_group', content='hello',
                                            continue_session=True,
                                            in_reply_to='msg1')
        self.check_reply(reply, success=True)
        self.assertEqual(self.app_worker.mock_calls['reply_to_group'], [
            (('msg1', 'hello'), {
                'continue_session': True, 'helper_metadata': {},
            }),
        ])

    @inlineCallbacks
    def test_handle_send_to(self):
        self.app_worker.mock_returns['send_to'] = succeed(None)
        reply = yield self.dispatch_command('send_to', content='hello',
                                            to_addr='1234',
                                            tag='default')
        self.check_reply(reply, success=True)
        self.assertEqual(self.app_worker.mock_calls['send_to'], [
            (('1234', 'hello'), {
                'endpoint': 'default', 'helper_metadata': {},
            }),
        ])

    def test_reply_to_fails_with_no_content(self):
        return self.assert_cmd_fails(
            "'content' must be given.",
            'reply_to', in_reply_to=u'known-id')

    def test_reply_to_fails_with_bad_content(self):
        return self.assert_cmd_fails(
            "'content' must be unicode or null.",
            'reply_to', content=5, in_reply_to=u'known-id')

    def test_reply_to_fails_with_no_in_reply_to(self):
        return self.assert_cmd_fails(
            "'in_reply_to' must be given.",
            'reply_to', content=u'foo')

    def test_reply_to_fails_with_bad_id(self):
        return self.assert_cmd_fails(
            "Could not find original message with id: u'unknown'",
            'reply_to', content='Hello?', in_reply_to=u'unknown')

    def test_reply_to_helper_metadata_not_allowed(self):
        return self.assert_cmd_fails(
            "'helper_metadata' is not allowed",
            'reply_to',
            to_addr='6789', content='bar', in_reply_to=u'known-id',
            helper_metadata={'go': {'conversation': 'someone-elses'}})

    def test_reply_to_helper_metadata_invalid(self):
        return self.assert_cmd_fails(
            "'helper_metadata' may only contain the following keys: voice",
            'reply_to',
            resource_config={'allowed_helper_metadata': ['voice']},
            to_addr='6789', content='bar', in_reply_to=u'known-id',
            helper_metadata={'go': {'conversation': 'someone-elses'}})

    def test_reply_to_helper_metadata_wrong_type(self):
        return self.assert_cmd_fails(
            "'helper_metadata' must be object or null.",
            'reply_to',
            resource_config={'allowed_helper_metadata': ['voice']},
            to_addr='6789', content='bar', in_reply_to=u'known-id',
            helper_metadata="Not a dict.")

    def test_reply_to_group_fails_with_no_content(self):
        return self.assert_cmd_fails(
            "'content' must be given.",
            'reply_to_group', in_reply_to=u'known-id')

    def test_reply_to_group_fails_with_no_in_reply_to(self):
        return self.assert_cmd_fails(
            "'in_reply_to' must be given.",
            'reply_to_group', content=u'foo')

    def test_reply_to_group_fails_with_bad_id(self):
        return self.assert_cmd_fails(
            "Could not find original message with id: u'unknown'",
            'reply_to_group', content='Hello?', in_reply_to=u'unknown')

    def test_reply_to_group_helper_metadata_not_allowed(self):
        return self.assert_cmd_fails(
            "'helper_metadata' is not allowed",
            'reply_to_group',
            to_addr='6789', content='bar', in_reply_to=u'known-id',
            helper_metadata={'go': {'conversation': 'someone-elses'}})

    def test_reply_to_group_helper_metadata_invalid(self):
        return self.assert_cmd_fails(
            "'helper_metadata' may only contain the following keys: voice",
            'reply_to_group',
            resource_config={'allowed_helper_metadata': ['voice']},
            to_addr='6789', content='bar', in_reply_to=u'known-id',
            helper_metadata={'go': {'conversation': 'someone-elses'}})
