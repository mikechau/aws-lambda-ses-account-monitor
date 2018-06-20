# -*- coding: utf-8 -*-
from collections import deque
from datetime import datetime

import boto3
import pytest
import responses

from botocore.stub import Stubber

from ses_account_monitor.configs.notify_config import NotifyConfig
from ses_account_monitor.monitor import Monitor
from ses_account_monitor.services import (
    CloudWatchService,
    SesService,
    SlackService)


@pytest.fixture
def notify_config():
    return NotifyConfig(notify_pager_duty_on_ses_reputation=True,
                        notify_pager_duty_on_ses_sending_quota=True,
                        notify_slack_on_ses_reputation=True,
                        notify_slack_on_ses_sending_quota=True)


@pytest.fixture
def ses_client():
    return boto3.client('ses',
                        aws_access_key_id='a',
                        aws_secret_access_key='b',
                        region_name='us-west-2')


@pytest.fixture
def ses_service(ses_client):
    return SesService(client=ses_client)


@pytest.fixture
def cloudwatch_client():
    return boto3.client('cloudwatch',
                        aws_access_key_id='a',
                        aws_secret_access_key='b',
                        region_name='us-west-2')


@pytest.fixture
def cloudwatch_service(cloudwatch_client):
    return CloudWatchService(client=cloudwatch_client)


@pytest.fixture
def slack_service():
    return SlackService(channels=['#general'], url='https://slack.com/webhook')


@pytest.fixture
def monitor(notify_config, ses_service, cloudwatch_service, slack_service):
    return Monitor(notify_config=notify_config, ses_service=ses_service, cloudwatch_service=cloudwatch_service, slack_service=slack_service)


@pytest.fixture
def target_datetime():
    return datetime(2018, 1, 1, 0, 0, 0, 0)


@pytest.fixture
def iso8601_datetime(target_datetime):
    return target_datetime.isoformat()


@pytest.fixture
def start_datetime():
    return datetime(2018, 6, 17, 1, 41, 25, 787402)


@pytest.fixture
def end_datetime():
    return datetime(2018, 6, 17, 2, 11, 25, 787402)


@pytest.fixture
def metric_data_results_response_critical(end_datetime):
    return {
        'MetricDataResults': [
            {
                'Id': 'bounce_rate',
                'Label': 'Bounce Rate',
                'Timestamps': [
                    end_datetime,
                ],
                'Values': [
                    0.05
                ],
                'StatusCode': 'Complete',
            },
            {
                'Id': 'complaint_rate',
                'Label': 'Complaint Rate',
                'Timestamps': [
                    end_datetime
                ],
                'Values': [
                    0.99
                ]
            }
        ],
        'NextToken': 'string'
    }


@pytest.fixture
def metric_data_results_response_warning(end_datetime):
    return {
        'MetricDataResults': [
            {
                'Id': 'bounce_rate',
                'Label': 'Bounce Rate',
                'Timestamps': [
                    end_datetime,
                ],
                'Values': [
                    0.054
                ],
                'StatusCode': 'Complete',
            },
            {
                'Id': 'complaint_rate',
                'Label': 'Complaint Rate',
                'Timestamps': [
                    end_datetime
                ],
                'Values': [
                    0.000000001
                ]
            }
        ],
        'NextToken': 'string'
    }


@pytest.fixture
def metric_data_results_response_ok(end_datetime):
    return {
        'MetricDataResults': [
            {
                'Id': 'bounce_rate',
                'Label': 'Bounce Rate',
                'Timestamps': [
                    end_datetime,
                ],
                'Values': [
                    0.03
                ],
                'StatusCode': 'Complete',
            },
            {
                'Id': 'complaint_rate',
                'Label': 'Complaint Rate',
                'Timestamps': [
                    end_datetime
                ],
                'Values': [
                    0.00001
                ]
            }
        ],
        'NextToken': 'string'
    }


@pytest.fixture
def metric_data_results_params(start_datetime, end_datetime):
    return {'EndTime': end_datetime,
            'MetricDataQueries': [{'Id': 'bounce_rate',
                                   'Label': 'Bounce Rate',
                                   'MetricStat': {'Metric': {'MetricName': 'Reputation.BounceRate',
                                                             'Namespace': 'AWS/SES'},
                                                  'Period': 900,
                                                  'Stat': 'Average'},
                                   'ReturnData': True},
                                  {'Id': 'complaint_rate',
                                   'Label': 'Complaint Rate',
                                   'MetricStat': {'Metric': {'MetricName': 'Reputation.ComplaintRate',
                                                             'Namespace': 'AWS/SES'},
                                                  'Period': 900,
                                                  'Stat': 'Average'},
                                   'ReturnData': True}],
            'StartTime': start_datetime}


def test_handle_ses_sending_quota_critical(monitor, target_datetime):
    ses_stubber = Stubber(monitor.ses_service.client)

    ses_stubber.add_response('get_send_quota',
                             {
                                 'Max24HourSend': 10.0,
                                 'MaxSendRate': 523.0,
                                 'SentLast24Hours': 15.0
                             },
                             {})

    ses_stubber.activate()

    result = monitor.handle_ses_sending_quota(target_datetime=target_datetime)

    assert len(result['pager_duty']) == 1
    assert result['pager_duty'][0] == {
        'client_url': 'https://undefined.console.aws.amazon.com/ses/?region=undefined',
        'dedup_key': 'undefined-undefined-undefined-ses-account-monitor/ses_account_sending_quota',
        'routing_key': None,
        'client': 'AWS Console',
        'event_action': 'trigger',
        'payload': {
            'custom_details': {
                'volume': 15.0,
                'aws_account_name': 'undefined',
                'max_volume': 10.0,
                'version': 'v1.2018.06.18',
                'utilization': '150%',
                'threshold': '90%',
                'aws_region': 'undefined',
                'ts': '2018-01-01T00:00:00',
                'aws_environment': 'undefined'},
            'source': 'undefined-undefined-undefined-ses-account-monitor',
            'group': 'aws-undefined',
            'severity': 'critical',
            'timestamp': '2018-01-01T00:00:00',
            'component': 'ses',
            'class': 'ses_account_sending_quota',
            'summary': 'SES account sending quota is at capacity.'}}


def test_handle_ses_sending_quota_warning(monitor, target_datetime):
    ses_stubber = Stubber(monitor.ses_service.client)

    ses_stubber.add_response('get_send_quota',
                             {
                                 'Max24HourSend': 10.0,
                                 'MaxSendRate': 523.0,
                                 'SentLast24Hours': 8.0
                             },
                             {})

    ses_stubber.activate()

    result = monitor.handle_ses_sending_quota(target_datetime=target_datetime)

    assert len(result['pager_duty']) == 1
    assert result['pager_duty'][0] == {
        'dedup_key': 'undefined-undefined-undefined-ses-account-monitor/ses_account_sending_quota',
        'event_action': 'resolve',
        'routing_key': None}
    assert len(result['slack']) == 1
    assert result['slack'][0] == {
        'attachments': [
            {'color': 'warning',
             'fallback': 'SES account sending rate has breached WARNING threshold.',
             'fields': [{'short': True,
                         'title': 'Service',
                         'value': '<https://undefined.console.aws.amazon.com/ses/?region=undefined|SES Account Sending>'},
                        {'short': True,
                         'title': 'Account',
                         'value': 'undefined'},
                        {'short': True,
                         'title': 'Region',
                         'value': 'undefined'},
                        {'short': True,
                         'title': 'Environment',
                         'value': 'undefined'},
                        {'short': True,
                         'title': 'Status',
                         'value': 'WARNING'},
                        {'title': 'Time (UTC)',
                         'value': '2018-01-01T00:00:00'},
                        {'short': True,
                         'title': 'Utilization',
                         'value': '80.00%'},
                        {'short': True,
                         'title': 'Threshold',
                         'value': '80.00%'},
                        {'short': True,
                         'title': 'Volume',
                         'value': 8.0},
                        {'short': True,
                         'title': 'Max Volume',
                         'value': 10.0},
                        {'short': False,
                         'title': 'Message',
                         'value': 'SES account sending rate has breached the WARNING threshold.'}],
             'footer': 'undefined-undefined-undefined-ses-account-monitor',
             'footer_icon': 'https://platform.slack-edge.com/img/default_application_icon.png',
             'ts': 1514793600}],
        'icon_emoji': None,
        'username': 'SES Account Monitor'}


def test_handle_ses_sending_quota_ok(monitor, target_datetime):
    ses_stubber = Stubber(monitor.ses_service.client)

    ses_stubber.add_response('get_send_quota',
                             {
                                 'Max24HourSend': 10.0,
                                 'MaxSendRate': 523.0,
                                 'SentLast24Hours': 5.0
                             },
                             {})

    ses_stubber.activate()

    result = monitor.handle_ses_sending_quota(target_datetime=target_datetime)

    assert result == {
        'slack': deque([]),
        'pager_duty': deque([{
            'event_action': 'resolve',
            'routing_key': None,
            'dedup_key': 'undefined-undefined-undefined-ses-account-monitor/ses_account_sending_quota'
        }])
    }


def test_handle_ses_reputation_critical(monitor, end_datetime, metric_data_results_response_critical, metric_data_results_params):
    cloudwatch_stubber = Stubber(monitor.cloudwatch_service.client)
    cloudwatch_stubber.add_response('get_metric_data',
                                    metric_data_results_response_critical,
                                    metric_data_results_params)

    cloudwatch_stubber.activate()

    result = monitor.handle_ses_reputation(target_datetime=end_datetime)

    assert len(result['pager_duty']) == 1
    assert result['pager_duty'][0] == {'client': 'AWS Console',
                                       'client_url': 'https://undefined.console.aws.amazon.com/ses/?region=undefined',
                                       'dedup_key': 'undefined-undefined-undefined-ses-account-monitor/ses_account_reputation',
                                       'event_action': 'trigger',
                                       'payload': {'class': 'ses_account_reputation',
                                                   'component': 'ses',
                                                   'custom_details': {'action': 'alert',
                                                                      'action_message': 'SES account is in danger of being suspended.',
                                                                      'aws_account_name': 'undefined',
                                                                      'aws_environment': 'undefined',
                                                                      'aws_region': 'undefined',
                                                                      'bounce_rate': '5.00%',
                                                                      'bounce_rate_threshold': '5.00%',
                                                                      'bounce_rate_timestamp': '2018-06-17T02:11:25.787402',
                                                                      'complaint_rate': '99.00%',
                                                                      'complaint_rate_threshold': '0.04%',
                                                                      'complaint_rate_timestamp': '2018-06-17T02:11:25.787402',
                                                                      'ts': '1529226685',
                                                                      'version': 'v1.2018.06.18'},
                                                   'group': 'aws-undefined',
                                                   'severity': 'critical',
                                                   'source': 'undefined-undefined-undefined-ses-account-monitor',
                                                   'summary': 'SES account reputation is at dangerous levels.',
                                                   'timestamp': '2018-06-17T02:11:25.787402'},
                                       'routing_key': None}

    assert len(result['slack']) == 1
    assert result['slack'][0] == {
        'attachments': [
            {'color': 'danger',
             'fallback': 'SES account reputation has breached CRITICAL threshold.',
             'fields': [{'short': True,
                         'title': 'Service',
                         'value': '<https://undefined.console.aws.amazon.com/ses/?region=undefined|SES Account Reputation>'},
                        {'short': True,
                         'title': 'Account',
                         'value': 'undefined'},
                        {'short': True,
                         'title': 'Region',
                         'value': 'undefined'},
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
                         'title': 'Complaint Rate / Threshold',
                         'value': '99.00% / 0.04%'},
                        {'short': True,
                         'title': 'Complaint Rate Time',
                         'value': '2018-06-17T02:11:25.787402'},
                        {'short': True,
                         'title': 'Bounce Rate / Threshold',
                         'value': '5.00% / 5.00%'},
                        {'short': True,
                         'title': 'Bounce Rate Time',
                         'value': '2018-06-17T02:11:25.787402'},
                        {'short': False,
                         'title': 'Message',
                         'value': 'SES account reputation has breached the CRITICAL threshold.'}],
             'footer': 'undefined-undefined-undefined-ses-account-monitor',
             'footer_icon': 'https://platform.slack-edge.com/img/default_application_icon.png',
             'ts': 1529226685}],
        'icon_emoji': None,
        'username': 'SES Account Monitor'}


def test_handle_ses_reputation_warning(monitor, end_datetime, metric_data_results_response_warning, metric_data_results_params):
    cloudwatch_stubber = Stubber(monitor.cloudwatch_service.client)
    cloudwatch_stubber.add_response('get_metric_data',
                                    metric_data_results_response_warning,
                                    metric_data_results_params)

    cloudwatch_stubber.activate()

    result = monitor.handle_ses_reputation(target_datetime=end_datetime)

    assert result['pager_duty'] == deque([])
    assert len(result['slack']) == 1
    assert result['slack'][0] == {
        'attachments': [
            {'color': 'warning',
             'fallback': 'SES account reputation has breached WARNING threshold.',
             'fields': [
                 {'short': True,
                  'title': 'Service',
                  'value': '<https://undefined.console.aws.amazon.com/ses/?region=undefined|SES Account Reputation>'},
                 {'short': True,
                  'title': 'Account',
                  'value': 'undefined'},
                 {'short': True,
                  'title': 'Region',
                  'value': 'undefined'},
                 {'short': True,
                  'title': 'Environment',
                  'value': 'undefined'},
                 {'short': True,
                  'title': 'Status',
                  'value': 'WARNING'},
                 {'short': True,
                  'title': 'Action',
                  'value': 'ALERT'},
                 {'short': True,
                  'title': 'Bounce Rate / Threshold',
                  'value': '5.40% / 5.00%'},
                 {'short': True,
                  'title': 'Bounce Rate Time',
                  'value': '2018-06-17T02:11:25.787402'},
                 {'short': False,
                  'title': 'Message',
                  'value': 'SES account reputation has breached the WARNING threshold.'}],
             'footer': 'undefined-undefined-undefined-ses-account-monitor',
             'footer_icon': 'https://platform.slack-edge.com/img/default_application_icon.png',
             'ts': 1529226685}],
        'icon_emoji': None,
        'username': 'SES Account Monitor'}


def test_handle_ses_reputation_ok(monitor, end_datetime, metric_data_results_response_ok, metric_data_results_params):
    cloudwatch_stubber = Stubber(monitor.cloudwatch_service.client)
    cloudwatch_stubber.add_response('get_metric_data',
                                    metric_data_results_response_ok,
                                    metric_data_results_params)

    cloudwatch_stubber.activate()

    result = monitor.handle_ses_reputation(target_datetime=end_datetime)

    assert result == {'pager_duty': deque([]), 'slack': deque([])}


@responses.activate
def test_send_notifications_critical(monitor, end_datetime, metric_data_results_response_critical, metric_data_results_params):
    ses_stubber = Stubber(monitor.ses_service.client)
    ses_stubber.add_response('get_send_quota',
                             {
                                 'Max24HourSend': 10.0,
                                 'MaxSendRate': 523.0,
                                 'SentLast24Hours': 15.0
                             },
                             {})
    ses_stubber.activate()

    cloudwatch_stubber = Stubber(monitor.cloudwatch_service.client)
    cloudwatch_stubber.add_response('get_metric_data',
                                    metric_data_results_response_critical,
                                    metric_data_results_params)
    cloudwatch_stubber.activate()

    with responses.RequestsMock(target='botocore.vendored.requests.adapters.HTTPAdapter.send') as rsps:
        rsps.add(
            responses.POST,
            monitor.pager_duty_service.url,
            status=202,
            json={
                'status': 'success',
                'message': 'Event processed',
                'dedup_key': 'samplekeyhere'
            }
        )

        rsps.add(
            responses.POST,
            monitor.slack_service.url,
            status=200,
            json={
                'ok': True
            }
        )

        monitor.handle_ses_sending_quota(target_datetime=end_datetime)
        monitor.handle_ses_reputation(target_datetime=end_datetime)
        result = monitor.send_notifications(raise_on_errors=True)

        assert len(result['pager_duty']) == 2
        assert len(result['slack']) == 2
