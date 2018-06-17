# -*- coding: utf-8 -*-
from datetime import datetime

import boto3
import pytest

from botocore.stub import Stubber
from ses_account_monitor.client.cloudwatch_client import CloudWatchClient


class TestWithHealthyMetrics():
    @pytest.fixture()
    def cloudwatch_client(self):
        return boto3.client('cloudwatch',
                            aws_access_key_id='a',
                            aws_secret_access_key='b',
                            region_name='us-west-2')

    @pytest.fixture()
    def start_datetime(self):
        return datetime(2018, 6, 17, 1, 41, 25, 787402)

    @pytest.fixture()
    def end_datetime(self):
        return datetime(2018, 6, 17, 2, 11, 25, 787402)

    @pytest.fixture()
    def current_datetime(self, end_datetime):
        return end_datetime

    @pytest.fixture()
    def cloudwatch_response(self, end_datetime):
        return {
            'MetricDataResults': [
                {
                    'Id': 'bounce_rate',
                    'Label': 'bounce_rate',
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
                    'Label': 'complaint_rate',
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
    def cloudwatch_expected_params(self, start_datetime, end_datetime):
        return {
            'StartTime': start_datetime,
            'MetricDataQueries': [{'Id': 'bounce_rate',
                                   'Label': 'bounce_rate',
                                   'MetricStat': {'Metric': {'MetricName': 'Reputation.BounceRate',
                                                             'Namespace': 'AWS/SES'},
                                                  'Period': 900,
                                                  'Stat': 'Average'},
                                   'ReturnData': True},
                                  {'Id': 'complaint_rate',
                                   'Label': 'complaint_rate',
                                   'MetricStat': {'Metric': {'MetricName': 'Reputation.ComplaintRate',
                                                             'Namespace': 'AWS/SES'},
                                                  'Period': 900,
                                                  'Stat': 'Average'},
                                   'ReturnData': True}],
            'EndTime': end_datetime
        }

    @pytest.fixture()
    def expected_results(self, current_datetime):
        return [{'Id': 'bounce_rate',
                 'Label': 'bounce_rate',
                 'StatusCode': 'Complete',
                 'Timestamps': [current_datetime],
                 'Values': [0.03]},
                {'Id': 'complaint_rate',
                 'Label': 'complaint_rate',
                 'Timestamps': [current_datetime],
                 'Values': [0.0001]}]

    def test_get_ses_reputation_metrics(self,
                                        cloudwatch_client,
                                        cloudwatch_response,
                                        cloudwatch_expected_params,
                                        end_datetime,
                                        expected_results):

        stubber = Stubber(cloudwatch_client)

        stubber.add_response('get_metric_data',
                             cloudwatch_response,
                             cloudwatch_expected_params)
        stubber.activate()

        client = CloudWatchClient(client=cloudwatch_client)
        results = client.get_ses_reputation_metrics(current_time=end_datetime)

        assert results == expected_results
