# -*- coding: utf-8 -*-
from datetime import datetime

import pytest
import responses

from ses_account_monitor.services.pager_duty_service import PagerDutyService


@pytest.fixture()
def webhook_url():
    return 'https://events.pagerduty.com/v2/enqueue'


@pytest.fixture()
def service(webhook_url):
    return PagerDutyService(url=webhook_url, routing_key='12345')


@pytest.fixture()
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
                                           'ts': '2018-01-01T00:00:00',
                                           'version': 'v1.2018.06.18'},
                        'group': 'aws-undefined',
                        'severity': 'critical',
                        'source': 'undefined-undefined-undefined-ses-account-monitor',
                        'summary': 'SES account sending quota is at capacity.',
                        'timestamp': '2018-01-01T00:00:00'},
            'routing_key': '12345'}


@pytest.fixture()
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
                                           'bounce_rate': '100.00%',
                                           'bounce_rate_threshold': '100.00%',
                                           'bounce_rate_timestamp': '2018-01-01 00:00:00',
                                           'complaint_rate': '100.00%',
                                           'complaint_rate_threshold': '100.00%',
                                           'complaint_rate_timestamp': '2018-01-01 00:00:00',
                                           'ts': '2018-01-01T00:00:00',
                                           'version': 'v1.2018.06.18'},
                        'group': 'aws-undefined',
                        'severity': 'critical',
                        'source': 'undefined-undefined-undefined-ses-account-monitor',
                        'summary': 'SES account reputation is at dangerous levels.',
                        'timestamp': '2018-01-01T00:00:00'},
            'routing_key': '12345'}


@pytest.fixture()
def build_resolve_event_payload():
    def _build_resolve_event_payload(target):
        return {'dedup_key': 'undefined-undefined-undefined-ses-account-monitor/{}'.format(target),
                'event_action': 'resolve',
                'routing_key': '12345'}

    return _build_resolve_event_payload


@pytest.fixture()
def iso8601_date():
    return datetime(2018, 1, 1, 0, 0, 0, 0).isoformat()


@pytest.fixture()
def metrics():
    return [('Bounce Rate', 1, 1, datetime(2018, 1, 1, 0, 0, 0, 0)),
            ('Complaint Rate', 1, 1, datetime(2018, 1, 1, 0, 0, 0, 0))]


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
                                                                           event_ts=iso8601_date,
                                                                           metric_ts=iso8601_date)

    assert result == ses_account_sending_quota_trigger_event_payload


def test_build_ses_account_sending_quota_resolve_event_payload(service, build_resolve_event_payload):
    result = service.build_ses_account_sending_quota_resolve_event_payload()

    assert result == build_resolve_event_payload('ses_account_sending_quota')


def test_build_ses_account_reputation_trigger_event_payload(service,
                                                            metrics,
                                                            ses_account_reputation_trigger_event_payload,
                                                            iso8601_date):
    result = service.build_ses_account_reputation_trigger_event_payload(metrics=metrics,
                                                                        event_ts=iso8601_date,
                                                                        metric_ts=iso8601_date,
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
                                                                event_ts=iso8601_date,
                                                                metric_ts=iso8601_date)

        service.enqueue_ses_account_sending_quota_resolve_event()

        service.enqueue_ses_account_reputation_trigger_event(metrics=metrics,
                                                             event_ts=iso8601_date,
                                                             metric_ts=iso8601_date)

        service.enqueue_ses_account_reputation_resolve_event()

        send_status, (request_1, request_2, request_3, request_4) = service.send_notifications()

        assert send_status is True
        assert request_1.status_code == 202
        assert request_2.status_code == 202
        assert request_3.status_code == 202
        assert request_4.status_code == 202
