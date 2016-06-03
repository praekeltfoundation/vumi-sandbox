# -*- test-case-name: go.apps.jsbox.tests.test_metrics -*-
# -*- coding: utf-8 -*-

"""Metrics for JS Box sandboxes"""

import re

from vxsandbox import SandboxResource
from twisted.internet.defer import inlineCallbacks
from vumi.errors import ConfigError

from vumi.blinkenlights.metrics import (
    SUM, AVG, MIN, MAX, LAST, MetricPublisher, Metric, MetricManager)


class MetricEventError(Exception):
    """Raised when a command cannot be converted to a metric event."""


class MetricEvent(object):

    AGGREGATORS = {
        'sum': SUM,
        'avg': AVG,
        'min': MIN,
        'max': MAX,
        'last': LAST
    }

    NAME_REGEX = re.compile(r"^[a-zA-Z][a-zA-Z0-9._-]{,100}$")

    def __init__(self, store, metric, value, agg):
        self.store = store
        self.metric = metric
        self.value = value
        self.agg = agg

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return all((self.store == other.store, self.metric == other.metric,
                    self.value == other.value, self.agg is other.agg))

    @classmethod
    def _parse_name(cls, name, kind):
        if name is None:
            raise MetricEventError("Missing %s name." % (kind,))
        if not isinstance(name, basestring):
            raise MetricEventError("Invalid type for %s name: %r"
                                   % (kind, name))
        if not cls.NAME_REGEX.match(name):
            raise MetricEventError("Invalid %s name: %r." % (kind, name))
        return name

    @classmethod
    def _parse_value(cls, value):
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise MetricEventError("Invalid metric value %r." % (value,))
        return value

    @classmethod
    def _parse_agg(cls, agg):
        if not isinstance(agg, basestring):
            raise MetricEventError("Invalid metric aggregator %r" % (agg,))
        if agg not in cls.AGGREGATORS:
            raise MetricEventError("Invalid metric aggregator %r." % (agg,))
        return cls.AGGREGATORS[agg]

    @classmethod
    def from_command(cls, command):
        store = cls._parse_name(command.get('store', 'default'), 'store')
        metric = cls._parse_name(command.get('metric'), 'metric')
        value = cls._parse_value(command.get('value'))
        agg = cls._parse_agg(command.get('agg'))
        return cls(store, metric, value, agg)


class MetricsResource(SandboxResource):
    """Resource that provides metric storing.

    :param string metrics_prefix:
        metrics prefix configuration.

    Example:
        Metric name will look something like this:
            'myprefix', 'mystore name'

    """
    @inlineCallbacks
    def setup(self):
        prefix = self.config.get('metrics_prefix', None)
        if prefix is None:
            raise ConfigError("metrics_prefix config parameter not supplied")
        self.metric_publisher = yield self.app_worker.start_publisher(
            MetricPublisher)

    def _metric_manager_prefix(self, store_name):
        prefix = self.config['metrics_prefix']
        return "%s.stores.%s." % (prefix, store_name)

    def _publish_event(self, api, ev):
        """Publish a metric event."""
        if ev.agg is not None:
            agg = [ev.agg]
        metric = Metric(ev.metric, agg)
        prefix = self._metric_manager_prefix(ev.store)
        manager = MetricManager(prefix, publisher=self.metric_publisher)
        manager.oneshot(metric, ev.value)
        manager.publish_metrics()

    def handle_fire(self, api, command):
        """Fire a metric value."""
        try:
            ev = MetricEvent.from_command(command)
        except MetricEventError, e:
            return self.reply(command, success=False, reason=unicode(e))
        self._publish_event(api, ev)
        return self.reply(command, success=True)
