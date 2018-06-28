# -*- coding: utf-8 -*-
from datetime import (
    datetime,
    timezone)

import pytest
import responses

from ses_account_monitor.services.slack_service import SlackService


@pytest.fixture
def webhook_url():
    return 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'


@pytest.fixture
def service(webhook_url):
    slack_service = SlackService(url=webhook_url, channels=['#general'])
    return slack_service


@pytest.fixture
def ses_account_sending_quota_payload():
    return {'attachments': [{'color': 'danger',
                             'fallback': 'SES account sending rate has breached CRITICAL threshold.',
                             'fields': [{'short': True,
                                         'title': 'Service',
                                         'value': '<https://None.console.aws.amazon.com/ses/home?region=None#dashboard:|SES Account Sending>'},
                                        {'short': True,
                                         'title': 'Account',
                                         'value': 'undefined'},
                                        {'short': True,
                                         'title': 'Region',
                                         'value': None},
                                        {'short': True,
                                         'title': 'Environment',
                                         'value': 'undefined'},
                                        {'short': True,
                                         'title': 'Status',
                                         'value': 'CRITICAL'},
                                        {'title': 'Time',
                                         'value': '2018-01-01T00:00:00+00:00'},
                                        {'short': True,
                                         'title': 'Utilization',
                                         'value': '100.00%'},
                                        {'short': True,
                                         'title': 'Threshold',
                                         'value': '90.00%'},
                                        {'short': True,
                                         'title': 'Volume',
                                         'value': 9000},
                                        {'short': True,
                                         'title': 'Max Volume',
                                         'value': 9000},
                                        {'short': False,
                                         'title': 'Message',
                                         'value': 'SES account sending rate has breached the CRITICAL threshold.'}],
                             'footer': 'undefined-None-undefined-ses-account-monitor',
                             'footer_icon': 'https://platform.slack-edge.com/img/default_application_icon.png',
                             'ts': 123456789}],
            'icon_emoji': None,
            'username': 'SES Account Monitor'}


@pytest.fixture
def ses_account_reputation_payload():
    return {'attachments': [
        {'color': 'danger',
         'fallback': 'SES account reputation has breached CRITICAL threshold.',
         'fields': [{'short': True,
                     'title': 'Service',
                     'value': '<https://None.console.aws.amazon.com/ses/home?region=None#reputation-dashboard:|SES Account Reputation>'},
                    {'short': True,
                     'title': 'Account',
                     'value': 'undefined'},
                    {'short': True,
                     'title': 'Region',
                     'value': None},
                    {'short': True,
                     'title': 'Environment',
                     'value': 'undefined'},
                    {'short': True,
                     'title': 'Status',
                     'value': 'CRITICAL'},
                    {'short': True,
                     'title': 'Action',
                     'value': 'ALERT'},
                    {'short': True,
                     'title': 'Bounce Rate / Threshold',
                     'value': '1.00% / 100.00%'},
                    {'short': True,
                     'title': 'Bounce Rate Time',
                     'value': '2018-01-01T00:00:00+00:00'},
                    {'short': True,
                     'title': 'Complaint Rate / Threshold',
                     'value': '1.00% / 100.00%'},
                    {'short': True,
                     'title': 'Complaint Rate Time',
                     'value': '2018-01-01T00:00:00+00:00'},
                    {'short': False,
                     'title': 'Message',
                     'value': 'SES account reputation has breached the CRITICAL threshold.'}],
         'footer': 'undefined-None-undefined-ses-account-monitor',
         'footer_icon': 'https://platform.slack-edge.com/img/default_application_icon.png',
         'ts': 123456789}],
        'icon_emoji': None,
        'username': 'SES Account Monitor'}


@responses.activate
def test_post_message(service, webhook_url):
    with responses.RequestsMock(target='botocore.vendored.requests.adapters.HTTPAdapter.send') as rsps:
        rsps.add(
            responses.POST,
            webhook_url,
            status=200,
            json={
                'ok': True
            }
        )

        result = service.post_json({})

        assert result.status_code == 200


@pytest.fixture
def iso8601_timestamp():
    dt = datetime(2018, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc).isoformat()
    return dt


@pytest.fixture
def metrics(iso8601_timestamp):
    return [('Bounce Rate', 1, 100, iso8601_timestamp),
            ('Complaint Rate', 1, 100, iso8601_timestamp)]


def test_build_ses_account_sending_quota_payload(service, ses_account_sending_quota_payload, iso8601_timestamp):
    result = service.build_ses_account_sending_quota_payload(threshold_name='CRITICAL',
                                                             utilization_percent=100,
                                                             threshold_percent=90,
                                                             volume=9000,
                                                             max_volume=9000,
                                                             event_unix_ts=123456789,
                                                             metric_iso_ts=iso8601_timestamp)

    assert result == ses_account_sending_quota_payload


def test_build_ses_account_reputation_payload(service, ses_account_reputation_payload, metrics):
    result = service.build_ses_account_reputation_payload(threshold_name='CRITICAL',
                                                          metrics=metrics,
                                                          event_unix_ts=123456789)

    assert result == ses_account_reputation_payload


@responses.activate
def test_send_notifications(service, webhook_url, metrics):
    with responses.RequestsMock(target='botocore.vendored.requests.adapters.HTTPAdapter.send') as rsps:
        rsps.add(
            responses.POST,
            webhook_url,
            status=200,
            json={
                'ok': True
            }
        )

        service.enqueue_ses_account_sending_quota_message(threshold_name='CRITICAL',
                                                          utilization_percent=100,
                                                          threshold_percent=90,
                                                          volume=9000,
                                                          max_volume=9000,
                                                          event_unix_ts=123456789)

        service.enqueue_ses_account_sending_quota_message(threshold_name='CRITICAL',
                                                          utilization_percent=100,
                                                          threshold_percent=90,
                                                          volume=9000,
                                                          max_volume=9000,
                                                          event_unix_ts=123456789)

        service.enqueue_ses_account_reputation_message(threshold_name='WARNING',
                                                       metrics=metrics,
                                                       event_unix_ts=123456789)

        send_status, requests = service.send_notifications()

        assert send_status is True

        for channel, request in requests:
            assert channel == '#general'
            assert request.status_code == 200
