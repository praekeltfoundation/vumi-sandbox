"""Tests for go.apps.jsbox.metrics."""

from twisted.internet.defer import inlineCallbacks
from vumi.tests.helpers import VumiTestCase
from vxsandbox.resources.tests.utils import ResourceTestCaseBase

from vxsandbox.resources.metrics import (
    MetricEvent, MetricEventError, MetricsResource)


class TestMetricEvent(VumiTestCase):

    SUM = MetricEvent.AGGREGATORS['sum']

    def test_create(self):
        ev = MetricEvent('mystore', 'foo', 2.0, self.SUM)
        self.assertEqual(ev.store, 'mystore')
        self.assertEqual(ev.metric, 'foo')
        self.assertEqual(ev.value, 2.0)
        self.assertEqual(ev.agg, self.SUM)

    def test_eq(self):
        ev1 = MetricEvent('mystore', 'foo', 1.5, self.SUM)
        ev2 = MetricEvent('mystore', 'foo', 1.5, self.SUM)
        self.assertEqual(ev1, ev2)

    def test_neq(self):
        ev1 = MetricEvent('mystore', 'foo', 1.5, self.SUM)
        ev2 = MetricEvent('mystore', 'bar', 1.5, self.SUM)
        self.assertNotEqual(ev1, ev2)

    def test_from_command(self):
        ev = MetricEvent.from_command({'store': 'mystore', 'metric': 'foo',
                                       'value': 1.5, 'agg': 'sum'})
        self.assertEqual(ev, MetricEvent('mystore', 'foo', 1.5, self.SUM))

    def test_bad_store(self):
        self.assertRaises(MetricEventError, MetricEvent.from_command, {
                'store': 'foo bar', 'metric': 'foo', 'value': 1.5,
                'agg': 'sum'})

    def test_bad_type_store(self):
        self.assertRaises(MetricEventError, MetricEvent.from_command, {
                'store': {}, 'metric': 'foo', 'value': 1.5,
                'agg': 'sum'})

    def test_bad_metric(self):
        self.assertRaises(MetricEventError, MetricEvent.from_command, {
                'store': 'mystore', 'metric': 'foo bar', 'value': 1.5,
                'agg': 'sum'})

    def test_bad_type_metric(self):
        self.assertRaises(MetricEventError, MetricEvent.from_command, {
                'store': 'mystore', 'metric': {}, 'value': 1.5,
                'agg': 'sum'})

    def test_missing_metric(self):
        self.assertRaises(MetricEventError, MetricEvent.from_command, {
                'store': 'mystore', 'value': 1.5, 'agg': 'sum'})

    def test_bad_value(self):
        self.assertRaises(MetricEventError, MetricEvent.from_command, {
                'store': 'mystore', 'metric': 'foo', 'value': 'abc',
                'agg': 'sum'})

    def test_bad_type_value(self):
        self.assertRaises(MetricEventError, MetricEvent.from_command, {
                'store': 'mystore', 'metric': 'foo', 'value': {},
                'agg': 'sum'})

    def test_missing_value(self):
        self.assertRaises(MetricEventError, MetricEvent.from_command, {
                'store': 'mystore', 'metric': 'foo', 'agg': 'sum'})

    def test_bad_agg(self):
        self.assertRaises(MetricEventError, MetricEvent.from_command, {
                'store': 'mystore', 'metric': 'foo', 'value': 1.5,
                'agg': 'foo'})

    def test_bad_type_agg(self):
        self.assertRaises(MetricEventError, MetricEvent.from_command, {
                'store': 'mystore', 'metric': 'foo', 'value': 1.5,
                'agg': {}})

    def test_missing_agg(self):
        self.assertRaises(MetricEventError, MetricEvent.from_command, {
                'store': 'mystore', 'metric': 'foo', 'value': 1.5})


class TestMetricsResource(ResourceTestCaseBase):

    PREFIX = 'test_metrics_prefix'
    SUM = MetricEvent.AGGREGATORS['sum']
    resource_cls = MetricsResource

    @inlineCallbacks
    def setUp(self):
        yield super(TestMetricsResource, self).setUp()
        yield self.create_resource({})

    def create_resource(self, config):
        config.setdefault('metrics_prefix', self.PREFIX)
        return super(TestMetricsResource, self).create_resource(config)

    @inlineCallbacks
    def check_publish(self, store, metric, value, agg):
        [metric_data] = yield self.app_helper.get_dispatched_metrics()
        [metric_datum] = metric_data
        [metric_name, aggs, points] = metric_datum
        [data_point] = points
        self.assertEqual(
            metric_name, "%s.stores.%s.%s" % (self.PREFIX, store, metric))
        self.assertEqual(aggs, [agg.name])
        self.assertEqual(data_point[1], value)

    @inlineCallbacks
    def check_not_published(self):
        metrics = yield self.app_helper.get_dispatched_metrics()
        self.assertEqual(metrics, [])

    @inlineCallbacks
    def test_handle_fire(self):
        reply = yield self.dispatch_command(
            'fire', metric="foo", value=1.5, agg='sum')
        self.check_reply(reply, success=True)
        yield self.check_publish('default', 'foo', 1.5, self.SUM)

    @inlineCallbacks
    def test_handle_fire_error(self):
        reply = yield self.dispatch_command(
            'fire', metric=u"foo bar", value=1.5, agg='sum')
        expected_error = "Invalid metric name: u'foo bar'."
        self.check_reply(reply, success=False)
        self.assertEqual(reply['reason'], expected_error)
        yield self.check_not_published()

    @inlineCallbacks
    def test_non_ascii_metric_name_error(self):
        reply = yield self.dispatch_command(
            'fire', metric=u"b\xe6r", value=1.5, agg='sum')
        expected_error = "Invalid metric name: u'b\\xe6r'."
        self.check_reply(reply, success=False)
        self.assertEqual(reply['reason'], expected_error)
        yield self.check_not_published()
