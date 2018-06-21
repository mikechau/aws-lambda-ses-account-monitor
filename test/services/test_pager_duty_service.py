# -*- coding: utf-8 -*-
from datetime import (
  datetime,
  timezone)

import pytest
import responses

from ses_account_monitor.services.pager_duty_service import PagerDutyService


@pytest.fixture
def webhook_url():
    return 'https://events.pagerduty.com/v2/enqueue'


@pytest.fixture
def service(webhook_url):
    return PagerDutyService(url=webhook_url, routing_key='12345')


@pytest.fixture
def ses_account_sending_quota_trigger_event_payload():
    return {'client': 'AWS Console',
            'client_url': 'https://undefined.console.aws.amazon.com/ses/?region=undefined',
            'dedup_key': 'undefined-undefined-undefined-ses-account-monitor/ses_account_sending_quota',
            'event_action': 'trigger',
            'payload': {'class': 'ses_account_sending_quota',
                        'component': 'ses',
                        'custom_details': {'aws_account_name': 'undefined',
                                           'aws_environment': 'undefined',
                                           'aws_region': 'undefined',
                                           'max_volume': 10,
                                           'volume': 10,
                                           'utilization': '100%',
                                           'threshold': '100%',
                                           'ts': '123456789',
                                           'version': 'v1.2018.06.18'},
                        'group': 'aws-undefined',
                        'severity': 'critical',
                        'source': 'undefined-undefined-undefined-ses-account-monitor',
                        'summary': 'SES account sending quota is at capacity.',
                        'timestamp': '2018-01-01T08:00:00+00:00'},
            'routing_key': '12345'}


@pytest.fixture
def ses_account_reputation_trigger_event_payload():
    return {'client': 'AWS Console',
            'client_url': 'https://undefined.console.aws.amazon.com/ses/?region=undefined',
            'dedup_key': 'undefined-undefined-undefined-ses-account-monitor/ses_account_reputation',
            'event_action': 'trigger',
            'payload': {'class': 'ses_account_reputation',
                        'component': 'ses',
                        'custom_details': {'action': 'disable',
                                           'action_message': 'SES account sending is disabled.',
                                           'aws_account_name': 'undefined',
                                           'aws_environment': 'undefined',
                                           'aws_region': 'undefined',
                                           'bounce_rate': '1.00%',
                                           'bounce_rate_threshold': '1.00%',
                                           'bounce_rate_timestamp': '2018-01-01T08:00:00+00:00',
                                           'complaint_rate': '1.00%',
                                           'complaint_rate_threshold': '1.00%',
                                           'complaint_rate_timestamp': '2018-01-01T08:00:00+00:00',
                                           'ts': '123456789',
                                           'version': 'v1.2018.06.18'},
                        'group': 'aws-undefined',
                        'severity': 'critical',
                        'source': 'undefined-undefined-undefined-ses-account-monitor',
                        'summary': 'SES account reputation is at dangerous levels.',
                        'timestamp': '2018-01-01T08:00:00+00:00'},
            'routing_key': '12345'}


@pytest.fixture
def build_resolve_event_payload():
    def _build_resolve_event_payload(target):
        return {'dedup_key': 'undefined-undefined-undefined-ses-account-monitor/{}'.format(target),
                'event_action': 'resolve',
                'routing_key': '12345'}

    return _build_resolve_event_payload


@pytest.fixture
def datetime_utc():
    dt = datetime(2018, 1, 1, 0, 0, 0, 0).astimezone(timezone.utc)
    return dt


@pytest.fixture
def iso8601_date(datetime_utc):
    return datetime_utc.isoformat()


@pytest.fixture
def metrics(iso8601_date):
    return [('Bounce Rate', 1, 1, iso8601_date),
            ('Complaint Rate', 1, 1, iso8601_date)]


@responses.activate
def test_post_message(service, webhook_url):
    with responses.RequestsMock(target='botocore.vendored.requests.adapters.HTTPAdapter.send') as rsps:
        rsps.add(
            responses.POST,
            webhook_url,
            status=202,
            json={
                'status': 'success',
                'message': 'Event processed',
                'dedup_key': 'samplekeyhere'
            }
        )

        result = service.post_json({})

        assert result.status_code == 202


def test_build_ses_account_sending_quota_trigger_event_payload(service, ses_account_sending_quota_trigger_event_payload, iso8601_date):
    result = service.build_ses_account_sending_quota_trigger_event_payload(volume=10,
                                                                           max_volume=10,
                                                                           utilization_percent=100,
                                                                           threshold_percent=100,
                                                                           event_iso_ts=iso8601_date,
                                                                           metric_ts=123456789)

    assert result == ses_account_sending_quota_trigger_event_payload


def test_build_ses_account_sending_quota_resolve_event_payload(service, build_resolve_event_payload):
    result = service.build_ses_account_sending_quota_resolve_event_payload()

    assert result == build_resolve_event_payload('ses_account_sending_quota')


def test_build_ses_account_reputation_trigger_event_payload(service,
                                                            metrics,
                                                            ses_account_reputation_trigger_event_payload,
                                                            iso8601_date):
    result = service.build_ses_account_reputation_trigger_event_payload(metrics=metrics,
                                                                        event_iso_ts=iso8601_date,
                                                                        event_unix_ts=123456789,
                                                                        action='disable')

    assert result == ses_account_reputation_trigger_event_payload


def test_build_ses_account_reputation_resolve_event_payload(service, build_resolve_event_payload):
    result = service.build_ses_account_reputation_resolve_event_payload()

    assert result == build_resolve_event_payload('ses_account_reputation')


def test_send_events(service, webhook_url, iso8601_date, metrics):
    with responses.RequestsMock(target='botocore.vendored.requests.adapters.HTTPAdapter.send') as rsps:
        rsps.add(
            responses.POST,
            webhook_url,
            status=202,
            json={
                'status': 'success',
                'message': 'Event processed',
                'dedup_key': 'samplekeyhere'
            }
        )

        service.enqueue_ses_account_sending_quota_trigger_event(volume=9001,
                                                                max_volume=9001,
                                                                utilization_percent=100,
                                                                threshold_percent=100,
                                                                event_iso_ts=iso8601_date,
                                                                metric_ts=123456789)

        service.enqueue_ses_account_sending_quota_resolve_event()

        service.enqueue_ses_account_reputation_trigger_event(metrics=metrics,
                                                             event_iso_ts=iso8601_date,
                                                             event_unix_ts=123456789)

        service.enqueue_ses_account_reputation_resolve_event()

        send_status, requests = service.send_notifications()

        assert send_status is True

        expected_eids = ['trigger::undefined-undefined-undefined-ses-account-monitor/ses_account_sending_quota',
                         'resolve::undefined-undefined-undefined-ses-account-monitor/ses_account_sending_quota',
                         'trigger::undefined-undefined-undefined-ses-account-monitor/ses_account_reputation',
                         'resolve::undefined-undefined-undefined-ses-account-monitor/ses_account_reputation']

        for idx, (eid, request) in enumerate(requests):
            assert eid == expected_eids[idx]
            assert request.status_code == 202
