# -*- test-case-name: vxsandbox.resources.tests.test_kv -*-

"""A Redis key-value store resource for Vumi's application sandbox."""

from __future__ import absolute_import

import logging
import json

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall
from twisted.python import log

from vumi.persist.txredis_manager import TxRedisManager

from .utils import SandboxResource


class RedisResource(SandboxResource):
    """
    Resource that provides access to a simple key-value store.

    Configuration options:

    :param dict redis_manager:
        Redis manager configuration options.
    :param int keys_per_user_soft:
        Maximum number of keys each user may make use of in redis
        before usage warnings are logged.
        (default: 80% of hard limit).
    :param int keys_per_user_hard:
        Maximum number of keys each user may make use of in redis
        (default: 100). Falls back to keys_per_user.
    :param int keys_per_user:
        Synonym for `keys_per_user_hard`. Deprecated.
    """

    @inlineCallbacks
    def setup(self):
        self.r_config = self.config.get('redis_manager', {})
        self.keys_per_user_hard = self.config.get(
            'keys_per_user_hard', self.config.get('keys_per_user', 100))
        self.keys_per_user_soft = self.config.get(
            'keys_per_user_soft', int(0.8 * self.keys_per_user_hard))
        self.redis = yield TxRedisManager.from_config(self.r_config)
        self.reconciler = Reconciler(self.redis)
        self.reconciler.start()

    @inlineCallbacks
    def teardown(self):
        yield self.reconciler.stop()
        yield self.redis.close_manager()

    def _count_key(self, sandbox_id):
        return "#".join(["count", sandbox_id])

    def _sandboxed_key(self, sandbox_id, key):
        return "#".join(["sandboxes", sandbox_id, key])

    def _too_many_keys(self, command):
        return self.reply(command, success=False,
                          reason="Too many keys")

    @inlineCallbacks
    def check_keys(self, api, key):
        if (yield self.redis.exists(key)):
            returnValue(True)
        count_key = self._count_key(api.sandbox_id)
        key_count = yield self.redis.incr(count_key, 1)
        if key_count > self.keys_per_user_soft:
            if key_count < self.keys_per_user_hard:
                api.log('Redis soft limit of %s keys reached for sandbox %s. '
                        'Once the hard limit of %s is reached no more keys '
                        'can be written.' % (
                            self.keys_per_user_soft,
                            api.sandbox_id,
                            self.keys_per_user_hard),
                        logging.WARNING)
            else:
                api.log('Redis hard limit of %s keys reached for sandbox %s. '
                        'No more keys can be written.' % (
                            self.keys_per_user_hard,
                            api.sandbox_id),
                        logging.ERROR)
                yield self.redis.incr(count_key, -1)
                returnValue(False)
        returnValue(True)

    @inlineCallbacks
    def handle_set(self, api, command):
        """
        Set the value of a key.

        Command fields:
            - ``key``: The key whose value should be set.
            - ``value``: The value to store. May be any JSON serializable
              object.
            - ``seconds``: Lifetime of the key in seconds. The default ``null``
              indicates that the key should not expire.

        Reply fields:
            - ``success``: ``true`` if the operation was successful, otherwise
              ``false``.

        Example:

        .. code-block:: javascript

            api.request(
                'kv.set',
                {key: 'foo',
                 value: {x: '42'}},
                function(reply) { api.log_info('Value store: ' +
                                               reply.success); });
        """
        key = self._sandboxed_key(api.sandbox_id, command.get('key'))
        seconds = command.get('seconds')
        if not (seconds is None or isinstance(seconds, (int, long))):
            returnValue(self.reply_error(
                command, "seconds must be a number or null"))
        if not (yield self.check_keys(api, key)):
            returnValue(self._too_many_keys(command))
        json_value = json.dumps(command.get('value'))
        if seconds is None:
            yield self.redis.set(key, json_value)
        else:
            yield self.redis.setex(key, seconds, json_value)
        returnValue(self.reply(command, success=True))

    @inlineCallbacks
    def handle_get(self, api, command):
        """
        Retrieve the value of a key.

        Command fields:
            - ``key``: The key whose value should be retrieved.

        Reply fields:
            - ``success``: ``true`` if the operation was successful, otherwise
              ``false``.
            - ``value``: The value retrieved.

        Example:

        .. code-block:: javascript

            api.request(
                'kv.get',
                {key: 'foo'},
                function(reply) {
                    api.log_info(
                        'Value retrieved: ' +
                        JSON.stringify(reply.value));
                }
            );
        """
        key = self._sandboxed_key(api.sandbox_id, command.get('key'))
        raw_value = yield self.redis.get(key)
        value = json.loads(raw_value) if raw_value is not None else None
        returnValue(self.reply(command, success=True,
                               value=value))

    @inlineCallbacks
    def handle_delete(self, api, command):
        """
        Delete a key.

        Command fields:
            - ``key``: The key to delete.

        Reply fields:
            - ``success``: ``true`` if the operation was successful, otherwise
              ``false``.

        Example:

        .. code-block:: javascript

            api.request(
                'kv.delete',
                {key: 'foo'},
                function(reply) {
                    api.log_info('Value deleted: ' +
                                 reply.success);
                }
            );
        """
        key = self._sandboxed_key(api.sandbox_id, command.get('key'))
        existed = bool((yield self.redis.delete(key)))
        if existed:
            count_key = self._count_key(api.sandbox_id)
            yield self.redis.incr(count_key, -1)
        returnValue(self.reply(command, success=True,
                               existed=existed))

    @inlineCallbacks
    def handle_incr(self, api, command):
        """
        Atomically increment the value of an integer key.

        The current value of the key must be an integer. If the key does not
        exist, it is set to zero.

        Command fields:
            - ``key``: The key to delete.
            - ``amount``: The integer amount to increment the key by. Defaults
              to 1.

        Reply fields:
            - ``success``: ``true`` if the operation was successful, otherwise
              ``false``.
            - ``value``: The new value of the key.

        Example:

        .. code-block:: javascript

            api.request(
                'kv.incr',
                {key: 'foo',
                 amount: 3},
                function(reply) {
                    api.log_info('New value: ' +
                                 reply.value);
                }
            );
        """
        key = self._sandboxed_key(api.sandbox_id, command.get('key'))
        if not (yield self.check_keys(api, key)):
            returnValue(self._too_many_keys(command))
        amount = command.get('amount', 1)
        try:
            value = yield self.redis.incr(key, amount=amount)
        except Exception, e:
            returnValue(self.reply(command, success=False, reason=unicode(e)))
        returnValue(self.reply(command, value=int(value), success=True))


class ReconciliationError(Exception):
    """
    Raised when an error occurs during reconciliation.
    """


class ReconciliationStatus(object):

    COMPLETE = 'complete'
    SCANNING = 'scanning'
    SAVING = 'saving'

    def __init__(self, redis):
        self._redis = redis

    @property
    def status(self):
        pass

    def load(self):
        """
        Load reconciliation status from Redis.
        """
        pass

    def save(self):
        """
        Save reconciliation status to Redis.
        """
        pass

    def complete(self):
        """
        Returns `True` if the reconciliation is complete, `False` otherwise.
        """
        return self.status == self.COMPLETE

    def scanning(self):
        """
        Returns `True` if the reconciliation is scanning Redis keys,
        `False` otherwise.
        """
        return self.status == self.SCANNING

    def saving(self):
        """
        Return `True` if the reconciliation is write sandbox key counts
        back to Redis, `False` otherwise.
        """
        return self.status == self.SAVING


class ReconciliationLock(object):
    def __init__(self, redis, expiry):
        self._redis = redis
        self._expiry = expiry

    def acquire(self):
        pass

    def release(self):
        pass


class Reconciler(object):
    """
    A task for reconciling key counts.

    Key counts are tracked accurately as keys are added or deleted,
    but keys that expire in Redis are never removed from a sandboxes
    key limit.

    :param TxRedisManager redis:
        Redis connection manager.

    :param int period:
        Seconds between reconciliation checks. Default is 600s.

    :param int recon_expiry:
        Seconds before a reconciliation is considered outdated.
        Default is one day.
    """

    DEFAULT_PERIOD = 10 * 60  # ten minutes
    DEFAULT_RECON_EXPIRY = 24 * 60 * 60  # one day

    work_fraction = 0.95  # fraction of the period to do work for

    def __init__(self, redis, period=None, recon_expiry=None):
        self._redis = redis
        self._period = period or self.DEFAULT_PERIOD
        self._recon_expiry = recon_expiry or self.DEFAULT_RECON_EXPIRY
        self._task = LoopingCall(self.attempt_reconciliation)
        self._done = None

    def _recon_key(self, *parts):
        return "#".join(["recon"] + parts)

    def _lock_key(self):
        return self._recon_key("lock")

    def start(self):
        """
        Start attempting reconciliation.
        """
        if self._done is None:
            self._done = self._task.start(self._period, now=False)
            self._done.addErrback(
                lambda failure: log.err(
                    failure, "Reconciliation task failed."))

    @inlineCallbacks
    def stop(self):
        """
        Stop attempting reconciliation.
        """
        if self._done is not None:
            self._task.stop()
            yield self._done
            self._done = None

    @inlineCallbacks
    def attempt_reconciliation(self):
        """
        Attempt to perform some reconciliation work.

        Only one worker performs reconciliation work at a time. This
        reduces load on Redis and simplifies the implementation.

        Work consists off:

        * Load the reconciliation status from Redis.
        * If no reconciliation is in progress and the last one was recent
          enough, no work is needed.
        * If there is a reconciliation in progress, continue scanning
          keys from where the work stopped, updating counts as needed.
        * After doing some work, write the results back to the reconciliation
          status in Redis.

        When a reconciliation is done:

        * Write the results to the sandbox key counts.
        * Make the reconciliation as complete and save the status in Redis.

        Work should continue for only one period and should wrap up when
        the task is stopped.
        """
        lock = ReconciliationLock(self._redis, expiry=self._period)
        start_time = self._task.clock.seconds()
        end_time = start_time + self._period * self.work_fraction

        def timeout():
            return self._task.clock.seconds() > end_time

        if not (yield lock.acquire()):
            return
        try:
            recon = ReconciliationStatus(self._redis, self._task.clock)
            yield recon.load()

            if recon.complete() and recon.expired():
                recon.reset()

            if recon.complete():
                return

            if recon.scanning():
                while (recon.scanning() and self._task.running
                       and not timeout()):
                    cursor = recon.scan_cursor()
                    cursor, keys = yield self._redis.scan(cursor, "match")
                    recon.update_scan(cursor, keys)
                yield recon.save()

            if recon.saving():
                while (recon.saving_counts() and self._task.running
                       and not timeout()):
                    sandbox_id, key_count = recon.pop_count()
                    yield self._redis.set("#%s" % sandbox_id, key_count)
                yield recon.save()
        finally:
            yield lock.release()
