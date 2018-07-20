# -*- coding: utf-8 -*-
from datetime import (
    datetime,
    timezone)

import boto3
import pytest

from botocore.stub import Stubber
from ses_account_monitor.services.cloudwatch_service import CloudWatchService


@pytest.fixture
def client():
    return boto3.client('cloudwatch',
                        aws_access_key_id='a',
                        aws_secret_access_key='b',
                        region_name='us-west-2')


@pytest.fixture
def service(client):
    return CloudWatchService(client=client)


@pytest.fixture
def start_datetime():
    return datetime(2018, 6, 17, 1, 41, 25, 787402, tzinfo=timezone.utc)


@pytest.fixture
def end_datetime():
    return datetime(2018, 6, 17, 2, 11, 25, 787402, tzinfo=timezone.utc)


@pytest.fixture
def current_datetime(end_datetime):
    return end_datetime


@pytest.fixture
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
                    0.03,
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
                    0.0000001
                ]
            }
        ],
        'NextToken': 'string'
    }


@pytest.fixture
def metric_data_results_params(start_datetime, end_datetime):
    return {
        'StartTime': start_datetime,
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
        'EndTime': end_datetime
    }


@pytest.fixture
def metric_data_results(current_datetime):
    return [{'Id': 'bounce_rate',
             'Label': 'Bounce Rate',
             'StatusCode': 'Complete',
             'Timestamps': [current_datetime],
             'Values': [0.03]},
            {'Id': 'complaint_rate',
             'Label': 'Complaint Rate',
             'Timestamps': [current_datetime],
             'Values': [0.0000001]}]


@pytest.fixture
def build_metric_data_results(current_datetime):
    def _build_metric_data_results(bounce_rate_value, complaint_rate_value):
        return [{'Id': 'bounce_rate',
                 'Label': 'Bounce Rate',
                 'StatusCode': 'Complete',
                 'Timestamps': [current_datetime],
                 'Values': [bounce_rate_value]},
                {'Id': 'complaint_rate',
                 'Label': 'Complaint Rate',
                 'Timestamps': [current_datetime],
                 'Values': [complaint_rate_value]}]
    return _build_metric_data_results


def test_get_ses_account_reputation_metric_data_results(client,
                                                        service,
                                                        metric_data_results_response,
                                                        metric_data_results_params,
                                                        end_datetime,
                                                        metric_data_results):

    stubber = Stubber(client)
    stubber.add_response('get_metric_data',
                         metric_data_results_response,
                         metric_data_results_params)

    with stubber:
        result = service.get_ses_account_reputation_metric_data(target_datetime=end_datetime)
        assert result == metric_data_results


def test_build_ses_account_reputation_metrics(service, build_metric_data_results):
    metric_data_results = build_metric_data_results(0.05, 0.1)
    result = service.build_ses_account_reputation_metrics(metric_data_results)

    assert result.critical == [('Complaint Rate', 10.0, 0.04, '2018-06-17T02:11:25.787402+00:00')]
    assert result.ok == []
    assert result.warning == [('Bounce Rate', 5.0, 5.0, '2018-06-17T02:11:25.787402+00:00')]


def test_get_ses_account_reputation_metrics(client,
                                            service,
                                            metric_data_results_response,
                                            metric_data_results_params,
                                            end_datetime):

    stubber = Stubber(client)
    stubber.add_response('get_metric_data',
                         metric_data_results_response,
                         metric_data_results_params)

    with stubber:
        result = service.get_ses_account_reputation_metrics(target_datetime=end_datetime)
        assert result.critical == []
        assert result.ok == [('Bounce Rate', 3.0, 5.0, '2018-06-17T02:11:25.787402+00:00'),
                             ('Complaint Rate', 0.00001, 0.01, '2018-06-17T02:11:25.787402+00:00')]
        assert result.warning == []
