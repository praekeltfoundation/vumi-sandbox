from twisted.internet.defer import inlineCallbacks

from vxsandbox.resources.tests.utils import ResourceTestCaseBase
from vxsandbox.resources.outbound import OutboundResource
from vxsandbox.tests.utils import DummyAppWorker


class StubbedAppWorker(DummyAppWorker):

    class DummyApi(DummyAppWorker.DummyApi):
        def __init__(self, inbound_messages):
            self._inbound_messages = inbound_messages

        def get_inbound_message(self, msg_id):
            return self._inbound_messages.get(msg_id)

    sandbox_api_cls = DummyApi

    def __init__(self, *args, **kw):
        super(StubbedAppWorker, self).__init__(*args, **kw)
        self._inbound_messages = {}
        self.ALLOWED_ENDPOINTS = set(self.ALLOWED_ENDPOINTS)

    def create_sandbox_api(self):
        return self.sandbox_api_cls(self._inbound_messages)

    def add_inbound_message(self, msg):
        self._inbound_messages[msg['message_id']] = msg

    def add_endpoint(self, endpoint):
        self.ALLOWED_ENDPOINTS.add(endpoint)


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
        outbounds = yield self.app_helper.get_dispatched_outbound()
        self.assertEqual(outbounds, [])

    @inlineCallbacks
    def assert_sent(self, to_addr, content, msg_options):
        [msg] = yield self.app_helper.get_dispatched_outbound()
        self.assertEqual(msg["to_addr"], to_addr)
        self.assertEqual(msg["content"], content)
        endpoint = msg_options.pop('endpoint', 'default')
        self.assertEqual(msg.get_routing_endpoint(), endpoint)
        for k, v in msg_options.items():
            self.assertEqual(msg[k], v)

    def mk_get_inbound_message(self, orig):
        def get_inbound_message(msg_id):
            if msg_id == orig["message_id"]:
                return orig
        return get_inbound_message

    @inlineCallbacks
    def test_reply_to(self):
        orig = self.app_helper.make_inbound('hi')
        self.api.get_inbound_message = self.mk_get_inbound_message(orig)
        reply = yield self.dispatch_command('reply_to', content='hello',
                                            continue_session=True,
                                            in_reply_to=orig["message_id"])
        self.check_reply(reply, success=True)
        self.assert_sent(orig["from_addr"], u'hello', {
            "in_reply_to": orig["message_id"],
            "session_event": None,
            "helper_metadata": {},
        })

    def assert_reply_to_fails(self, reason, **kw):
        return self.assert_cmd_fails(reason, 'reply_to', **kw)

    def test_reply_to_fails_with_no_content(self):
        return self.assert_reply_to_fails(
            "'content' must be given.", in_reply_to=u'known-id')

    def test_reply_to_fails_with_bad_content(self):
        return self.assert_reply_to_fails(
            "'content' must be unicode or null.",
            content=5, in_reply_to=u'known-id')

    def test_reply_to_fails_with_no_in_reply_to(self):
        return self.assert_reply_to_fails(
            "'in_reply_to' must be given.", content=u'foo')

    def test_reply_to_fails_with_bad_id(self):
        return self.assert_reply_to_fails(
            "Could not find original message with id: u'unknown'",
            content='Hello?', in_reply_to=u'unknown')

    def test_reply_to_helper_metadata_not_allowed(self):
        return self.assert_reply_to_fails(
            "'helper_metadata' is not allowed",
            to_addr='6789', content='bar', in_reply_to=u'known-id',
            helper_metadata={'go': {'conversation': 'someone-elses'}})

    def test_reply_to_helper_metadata_invalid(self):
        return self.assert_reply_to_fails(
            "'helper_metadata' may only contain the following keys: voice",
            resource_config={'allowed_helper_metadata': ['voice']},
            to_addr='6789', content='bar', in_reply_to=u'known-id',
            helper_metadata={'go': {'conversation': 'someone-elses'}})

    def test_reply_to_helper_metadata_wrong_type(self):
        return self.assert_reply_to_fails(
            "'helper_metadata' must be object or null.",
            resource_config={'allowed_helper_metadata': ['voice']},
            to_addr='6789', content='bar', in_reply_to=u'known-id',
            helper_metadata="Not a dict.")

    @inlineCallbacks
    def test_reply_to_group(self):
        orig = self.app_helper.make_inbound('hi', group="#channel")
        self.api.get_inbound_message = self.mk_get_inbound_message(orig)
        reply = yield self.dispatch_command('reply_to_group', content='hello',
                                            continue_session=True,
                                            in_reply_to=orig["message_id"])
        self.check_reply(reply, success=True)
        self.assert_sent(None, u'hello', {
            "in_reply_to": orig["message_id"],
            "group": "#channel",
            "session_event": None,
            "helper_metadata": {},
        })

    def assert_reply_to_group_fails(self, reason, **kw):
        return self.assert_cmd_fails(reason, 'reply_to_group', **kw)

    def test_reply_to_group_fails_with_no_content(self):
        return self.assert_reply_to_group_fails(
            "'content' must be given.", in_reply_to=u'known-id')

    def test_reply_to_group_fails_with_no_in_reply_to(self):
        return self.assert_reply_to_group_fails(
            "'in_reply_to' must be given.", content=u'foo')

    def test_reply_to_group_fails_with_bad_id(self):
        return self.assert_reply_to_group_fails(
            "Could not find original message with id: u'unknown'",
            content='Hello?', in_reply_to=u'unknown')

    def test_reply_to_group_helper_metadata_not_allowed(self):
        return self.assert_reply_to_group_fails(
            "'helper_metadata' is not allowed",
            to_addr='6789', content='bar', in_reply_to=u'known-id',
            helper_metadata={'go': {'conversation': 'someone-elses'}})

    def test_reply_to_group_helper_metadata_invalid(self):
        return self.assert_reply_to_group_fails(
            "'helper_metadata' may only contain the following keys: voice",
            resource_config={'allowed_helper_metadata': ['voice']},
            to_addr='6789', content='bar', in_reply_to=u'known-id',
            helper_metadata={'go': {'conversation': 'someone-elses'}})

    @inlineCallbacks
    def test_send_to(self):
        reply = yield self.dispatch_command(
            'send_to', content='hello', to_addr='1234')
        self.check_reply(reply, success=True)
        yield self.assert_sent(u'1234', u'hello', {
            'endpoint': 'default',
            'helper_metadata': {},
            'in_reply_to': None,
        })

    @inlineCallbacks
    def test_send_to_with_endpoint(self):
        self.app_worker.add_endpoint('extra_endpoint')
        reply = yield self.dispatch_command(
            'send_to', content='hello', to_addr='1234',
            endpoint='extra_endpoint')
        self.check_reply(reply, success=True)
        yield self.assert_sent(u'1234', u'hello', {
            'endpoint': 'extra_endpoint',
            'helper_metadata': {},
            'in_reply_to': None,
        })

    def assert_send_to_fails(self, reason, **kw):
        return self.assert_cmd_fails(reason, 'send_to', **kw)

    def test_send_to_unconfigured_endpoint(self):
        return self.assert_send_to_fails(
            "Endpoint u'bad_endpoint' not configured",
            endpoint='bad_endpoint', to_addr='6789',
            content='bar')

    def test_send_to_missing_content(self):
        return self.assert_send_to_fails(
            "'content' must be given.",
            endpoint='extra_endpoint', to_addr='6789')

    def test_send_to_bad_content(self):
        return self.assert_send_to_fails(
            "'content' must be unicode or null.",
            content=3, endpoint='extra_endpoint', to_addr='6789')

    def test_send_to_bad_endpoint(self):
        return self.assert_send_to_fails(
            "'endpoint' must be given in sends.",
            endpoint=None, to_addr='6789', content='bar')

    def test_send_to_missing_to_addr(self):
        return self.assert_send_to_fails(
            "'to_addr' must be given in sends.",
            endpoint='extra_endpoint', content='bar')

    def test_send_to_bad_to_addr(self):
        return self.assert_send_to_fails(
            "'to_addr' must be given in sends.",
            to_addr=None, endpoint='extra_endpoint', content='bar')

    def test_send_to_helper_metadata_not_allowed(self):
        return self.assert_send_to_fails(
            "'helper_metadata' is not allowed",
            to_addr='6789', endpoint='default', content='bar',
            helper_metadata={'foo': 'not-allowed'})

    def test_send_to_helper_metadata_invalid(self):
        return self.assert_send_to_fails(
            "'helper_metadata' may only contain the following keys: voice",
            resource_config={'allowed_helper_metadata': ['voice']},
            to_addr='6789', endpoint='default', content='bar',
            helper_metadata={'foo': 'not-allowed'})

    @inlineCallbacks
    def test_send_to_endpoint(self):
        self.app_worker.add_endpoint('extra_endpoint')
        yield self.create_resource({})
        reply = yield self.dispatch_command(
            'send_to_endpoint', endpoint='extra_endpoint', to_addr='6789',
            content='bar')
        self.check_reply(reply)
        yield self.assert_sent('6789', 'bar', {
            'endpoint': 'extra_endpoint',
            'helper_metadata': {},
            'in_reply_to': None,
        })

    @inlineCallbacks
    def test_send_to_endpoint_null_content(self):
        self.app_worker.add_endpoint('extra_endpoint')
        yield self.create_resource({})
        reply = yield self.dispatch_command(
            'send_to_endpoint', endpoint='extra_endpoint', to_addr='6789',
            content=None)
        self.check_reply(reply)
        yield self.assert_sent(u'6789', None, {
            'endpoint': 'extra_endpoint',
            'helper_metadata': {},
            'in_reply_to': None,
        })

    @inlineCallbacks
    def test_send_to_endpoint_with_helper_metadata(self):
        self.app_worker.add_endpoint('extra_endpoint')
        yield self.create_resource({
            'allowed_helper_metadata': ['voice'],
        })

        reply = yield self.dispatch_command(
            'send_to_endpoint', endpoint='extra_endpoint', to_addr='6789',
            content='bar',
            helper_metadata={
                'voice': {
                    'speech_url': 'http://www.example.com/audio.wav',
                },
            })
        self.check_reply(reply)
        yield self.assert_sent(u'6789', u'bar', {
            'endpoint': 'extra_endpoint',
            'helper_metadata': {
                'voice': {
                    'speech_url': 'http://www.example.com/audio.wav',
                },
            },
            'in_reply_to': None,
        })

    def assert_send_to_endpoint_fails(self, reason, **kw):
        return self.assert_cmd_fails(reason, 'send_to_endpoint', **kw)

    def test_send_to_endpoint_not_configured(self):
        return self.assert_send_to_endpoint_fails(
            "Endpoint u'bad_endpoint' not configured",
            endpoint='bad_endpoint', to_addr='6789',
            content='bar')

    def test_send_to_endpoint_missing_content(self):
        return self.assert_send_to_endpoint_fails(
            "'content' must be given.",
            endpoint='extra_endpoint', to_addr='6789')

    def test_send_to_endpoint_bad_content(self):
        return self.assert_send_to_endpoint_fails(
            "'content' must be unicode or null.",
            content=3, endpoint='extra_endpoint', to_addr='6789')

    def test_send_to_endpoint_missing_endpoint(self):
        return self.assert_send_to_endpoint_fails(
            "'endpoint' must be given in sends.",
            to_addr='6789', content='bar')

    def test_send_to_endpoint_bad_endpoint(self):
        return self.assert_send_to_endpoint_fails(
            "'endpoint' must be given in sends.",
            endpoint=None, to_addr='6789', content='bar')

    def test_send_to_endpoint_missing_to_addr(self):
        return self.assert_send_to_endpoint_fails(
            "'to_addr' must be given in sends.",
            endpoint='extra_endpoint', content='bar')

    def test_send_to_endpoint_bad_to_addr(self):
        return self.assert_send_to_endpoint_fails(
            "'to_addr' must be given in sends.",
            to_addr=None, endpoint='extra_endpoint', content='bar')

    def test_send_to_endpoint_helper_metadata_not_allowed(self):
        return self.assert_send_to_endpoint_fails(
            "'helper_metadata' is not allowed",
            to_addr='6789', endpoint='default', content='bar',
            helper_metadata={'foo': 'not-allowed'})

    def test_send_to_endpoint_helper_metadata_invalid(self):
        return self.assert_send_to_endpoint_fails(
            "'helper_metadata' may only contain the following keys: voice",
            resource_config={'allowed_helper_metadata': ['voice']},
            to_addr='6789', endpoint='default', content='bar',
            helper_metadata={'foo': 'not-allowed'})
