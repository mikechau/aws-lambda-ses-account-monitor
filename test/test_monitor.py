# -*- coding: utf-8 -*-
from collections import deque
from datetime import datetime

import boto3
import pytest

from botocore.stub import Stubber

from ses_account_monitor.configs.notify_config import NotifyConfig
from ses_account_monitor.monitor import Monitor
from ses_account_monitor.services import (
    CloudWatchService,
    SesService)


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
def monitor(notify_config, ses_service, cloudwatch_service):
    return Monitor(notify_config=notify_config, ses_service=ses_service, cloudwatch_service=cloudwatch_service)


@pytest.fixture
def target_datetime():
    return datetime(2018, 1, 1, 0, 0, 0, 0)


@pytest.fixture
def iso8601_datetime(target_datetime):
    return target_datetime.isoformat()


@pytest.fixture()
def start_datetime():
    return datetime(2018, 6, 17, 1, 41, 25, 787402)


@pytest.fixture()
def end_datetime():
    return datetime(2018, 6, 17, 2, 11, 25, 787402)


@pytest.fixture()
def metric_data_results_response(end_datetime):
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
                    0.0001
                ]
            }
        ],
        'NextToken': 'string'
    }


@pytest.fixture()
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

    assert len(result['pagerduty']) == 1
    assert result['pagerduty'][0] == {
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

    assert len(result['pagerduty']) == 1
    assert result['pagerduty'][0] == {
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
        'pagerduty': deque([{
            'event_action': 'resolve',
            'routing_key': None,
            'dedup_key': 'undefined-undefined-undefined-ses-account-monitor/ses_account_sending_quota'
        }])
    }


def test_handle_ses_reputation_critical(monitor, end_datetime, metric_data_results_response, metric_data_results_params):
    cloudwatch_stubber = Stubber(monitor.cloudwatch_service.client)
    cloudwatch_stubber.add_response('get_metric_data',
                                    metric_data_results_response,
                                    metric_data_results_params)

    cloudwatch_stubber.activate()

    result = monitor.handle_ses_reputation(target_datetime=end_datetime)

    assert result is None
