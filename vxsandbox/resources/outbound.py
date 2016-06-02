# -*- test-case-name: vxsandbox.resources.tests.test_outbound -*-

"""An outbound message sending for Vumi's application sandbox."""

from twisted.internet.defer import succeed

from vumi.errors import InvalidEndpoint

from .utils import SandboxResource


class InvalidOutboundCommand(Exception):
    """
    Internal exception raised when a sandboxed application sends
    and invalid outbound command.
    """


class OutboundResource(SandboxResource):
    """
    Resource that provides the ability to send outbound messages.

    Includes support for replying to the sender of the current message,
    replying to the group the current message was from and sending messages
    that aren't replies.
    """

    def setup(self):
        self._allowed_helper_metadata = set(
            self.config.get('allowed_helper_metadata', []))

    def _mkfail(self, command, reason):
        return self.reply(command, success=False, reason=reason)

    def _mkfaild(self, command, reason):
        return succeed(self._mkfail(command, reason))

    def _reply_callbacks(self, command):
        callback = lambda r: self.reply(command, success=True)
        errback = lambda f: self._mkfail(command, unicode(f.getErrorMessage()))
        return (callback, errback)

    def _get_cmd_params(self, api, command, params):
        return [
            getattr(self, '_param_%s' % name)(api, command) for name in params
        ]

    def _param_content(self, api, command):
        if 'content' not in command:
            raise InvalidOutboundCommand(u"'content' must be given.")
        content = command['content']
        if not isinstance(content, (unicode, type(None))):
            raise InvalidOutboundCommand("'content' must be unicode or null.")
        return content

    def _param_continue_session(self, api, command):
        continue_session = command.get('continue_session', True)
        if continue_session not in (True, False):
            raise InvalidOutboundCommand(
                u"'continue_session' must be either true or false if given")
        return continue_session

    def _param_in_reply_to(self, api, command):
        in_reply_to = command.get('in_reply_to')
        if not isinstance(in_reply_to, unicode):
            raise InvalidOutboundCommand(u"'in_reply_to' must be given.")
        orig_msg = api.get_inbound_message(in_reply_to)
        if orig_msg is None:
            raise InvalidOutboundCommand(
                u"Could not find original message with id: %r" % in_reply_to)
        return orig_msg

    def _param_helper_metadata(self, api, command):
        helper_metadata = command.get('helper_metadata')
        if helper_metadata in [None, {}]:
            # No helper metadata, so return an empty dict.
            return {}
        if not self._allowed_helper_metadata:
            raise InvalidOutboundCommand("'helper_metadata' is not allowed")
        if not isinstance(helper_metadata, dict):
            raise InvalidOutboundCommand(
                "'helper_metadata' must be object or null.")
        if any(key not in self._allowed_helper_metadata
               for key in helper_metadata.iterkeys()):
            raise InvalidOutboundCommand(
                "'helper_metadata' may only contain the following keys: %s"
                % ', '.join(sorted(self._allowed_helper_metadata)))
        # Anything we have left is valid.
        return helper_metadata

    def _param_endpoint(self, api, command):
        endpoint = command.get('endpoint')
        if not isinstance(endpoint, unicode):
            raise InvalidOutboundCommand(
                u"'endpoint' must be given in sends.")
        try:
            self.app_worker.check_endpoint(
                self.app_worker.ALLOWED_ENDPOINTS, endpoint)
        except InvalidEndpoint:
            raise InvalidOutboundCommand(
                u"Endpoint %r not configured" % (endpoint,))
        return endpoint

    def _param_to_addr(self, api, command):
        to_addr = command.get('to_addr')
        if not isinstance(to_addr, unicode):
            raise InvalidOutboundCommand(u"'to_addr' must be given in sends.")
        return to_addr

    def handle_reply_to(self, api, command):
        """
        Sends a reply to the individual who sent a received message.

        Command fields:
            - ``content``: The body of the reply message.
            - ``in_reply_to``: The ``message id`` of the message being replied
              to.
            - ``continue_session``: Whether to continue the session (if any).
              Defaults to ``true``.
            - ``helper_metadata``: An object of additional helper metadata
              fields to include in the reply.

        Reply fields:
            - ``success``: ``true`` if the operation was successful, otherwise
              ``false``.

        Example:

        .. code-block:: javascript

            api.request(
                'outbound.reply_to',
                {content: 'Welcome!',
                 in_reply_to: '06233d4eede945a3803bf9f3b78069ec'},
                function(reply) { api.log_info('Reply sent: ' +
                                               reply.success); });
        """
        try:
            content, orig_msg, continue_session, helper_metadata = (
                self._get_cmd_params(api, command, [
                    'content', 'in_reply_to', 'continue_session',
                    'helper_metadata']))
        except InvalidOutboundCommand, err:
            return self._mkfaild(command, reason=unicode(err))

        d = self.app_worker.reply_to(
            orig_msg, content, continue_session=continue_session,
            helper_metadata=helper_metadata)
        return d.addCallbacks(*self._reply_callbacks(command))

    def handle_reply_to_group(self, api, command):
        """
        Sends a reply to the group from which a received message was sent.

        Command fields:
            - ``content``: The body of the reply message.
            - ``in_reply_to``: The ``message id`` of the message being replied
              to.
            - ``continue_session``: Whether to continue the session (if any).
              Defaults to ``true``.
            - ``helper_metadata``: An object of additional helper metadata
              fields to include in the reply.

        Reply fields:
            - ``success``: ``true`` if the operation was successful, otherwise
              ``false``.

        Example:

        .. code-block:: javascript

            api.request(
                'outbound.reply_to_group',
                {content: 'Welcome!',
                 in_reply_to: '06233d4eede945a3803bf9f3b78069ec'},
                function(reply) { api.log_info('Reply to group sent: ' +
                                               reply.success); });
        """
        try:
            content, orig_msg, continue_session, helper_metadata = (
                self._get_cmd_params(api, command, [
                    'content', 'in_reply_to', 'continue_session',
                    'helper_metadata']))
        except InvalidOutboundCommand, err:
            return self._mkfaild(command, reason=unicode(err))

        d = self.app_worker.reply_to_group(
            orig_msg, content, continue_session=continue_session,
            helper_metadata=helper_metadata)
        return d.addCallbacks(*self._reply_callbacks(command))

    def handle_send_to(self, api, command):
        """
        Sends a message to a specified address.

        Command fields:
            - ``content``: The body of the reply message.
            - ``to_addr``: The address of the recipient (e.g. an MSISDN).
            - ``endpoint``: The name of the endpoint to send the message via.
              Optional (default is ``"default"``).
            - ``helper_metadata``: An object of additional helper metadata
              fields to include in the message being sent.

        Reply fields:
            - ``success``: ``true`` if the operation was successful, otherwise
              ``false``.

        Example:

        .. code-block:: javascript

            api.request(
                'outbound.send_to',
                {content: 'Welcome!', to_addr: '+27831234567',
                 endpoint: 'default'},
                function(reply) { api.log_info('Message sent: ' +
                                               reply.success); });
        """
        if 'endpoint' not in command:
            command['endpoint'] = u'default'
        try:
            content, to_addr, endpoint, helper_metadata = (
                self._get_cmd_params(api, command, [
                    'content', 'to_addr', 'endpoint', 'helper_metadata']))
        except InvalidOutboundCommand, err:
            return self._mkfaild(command, reason=unicode(err))

        d = self.app_worker.send_to(
            to_addr, content, endpoint=endpoint,
            helper_metadata=helper_metadata)
        return d.addCallbacks(*self._reply_callbacks(command))

    def handle_send_to_endpoint(self, api, command):
        """
        Sends a message to a specified endpoint.
        Command fields:
            - ``content``: The body of the reply message.
            - ``to_addr``: The address of the recipient (e.g. an MSISDN).
            - ``endpoint``: The name of the endpoint to send the message via.
            - ``helper_metadata``: An object of additional helper metadata
              fields to include in the message being sent.
        Reply fields:
            - ``success``: ``true`` if the operation was successful, otherwise
              ``false``.
        Example:
        .. code-block:: javascript
            api.request(
                'outbound.send_to_endpoint',
                {content: 'Welcome!', to_addr: '+27831234567',
                 endpoint: 'sms'},
                function(reply) { api.log_info('Message sent: ' +
                                               reply.success); });
        """
        try:
            content, to_addr, endpoint, helper_metadata = (
                self._get_cmd_params(api, command, [
                    'content', 'to_addr', 'endpoint', 'helper_metadata']))
        except InvalidOutboundCommand, err:
            return self._mkfaild(command, reason=unicode(err))

        d = self.app_worker.send_to(
            to_addr, content, endpoint=endpoint,
            helper_metadata=helper_metadata)
        return d.addCallbacks(*self._reply_callbacks(command))
