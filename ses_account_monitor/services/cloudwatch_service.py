# -*- coding: utf-8 -*-
import logging

from collections import namedtuple

from datetime import (
    datetime,
    timedelta)

import boto3

from ses_account_monitor.config import (
    LAMBDA_AWS_SESSION_CONFIG,
    SES_REPUTATION_PERIOD,
    SES_REPUTATION_PERIOD_TIMEDELTA,
    SES_THRESHOLDS,
    THRESHOLD_CRITICAL,
    THRESHOLD_WARNING)
from ses_account_monitor.util import (
    json_dump_request_event,
    json_dump_response_event)


SesReputationMetrics = namedtuple('SesReputationMetrics', ('critical',
                                                           'ok',
                                                           'warning'))


class CloudWatchService(object):
    def __init__(self,
                 client=None,
                 logger=None,
                 session_config=None,
                 ses_thresholds=None,
                 ses_reputation_period=None,
                 ses_reputation_period_timedelta=None):

        self._session_config = (session_config or LAMBDA_AWS_SESSION_CONFIG)

        self.ses_thresholds = (ses_thresholds or SES_THRESHOLDS)
        self.ses_reputation_period = (ses_reputation_period or SES_REPUTATION_PERIOD)
        self.ses_reputation_period_timedelta = (ses_reputation_period_timedelta or SES_REPUTATION_PERIOD_TIMEDELTA)

        self._set_client(client)
        self._set_logger(logger)

    @property
    def client(self):
        return self._client

    @property
    def logger(self):
        return self._logger

    def get_ses_account_reputation_metrics(self, current_time=None, period=None, period_timedelta=None):
        metric_data = self.get_ses_account_reputation_metric_data(current_time=current_time,
                                                                  period=period,
                                                                  period_timedelta=period_timedelta)

        return self.build_ses_account_reputation_metrics(metric_data)

    def get_ses_account_reputation_metric_data(self, current_time=None, period=None, period_timedelta=None):
        self.logger.debug('Fetching SES account reputation metrics...')

        params = self.get_ses_account_reputation_metric_params(
            current_time=current_time,
            period=period,
            period_timedelta=period_timedelta)

        self._log_get_ses_account_reputation_metrics_request(params)

        response = self.client.get_metric_data(**params)

        self._log_get_ses_account_reputation_metrics_response(response)

        return response['MetricDataResults']

    def get_ses_account_reputation_metric_params(self, current_time=None, period=None, period_timedelta=None):
        if period is None:
            period = self.ses_reputation_period

        if period_timedelta is None:
            period_timedelta = self.ses_reputation_period_timedelta

        if current_time is None:
            current_time = datetime.utcnow()

        return {
            'MetricDataQueries': [
                {
                    'Id': 'bounce_rate',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/SES',
                            'MetricName': 'Reputation.BounceRate'
                        },
                        'Period': period,
                        'Stat': 'Average'
                    },
                    'Label': 'Bounce Rate',
                    'ReturnData': True
                },
                {
                    'Id': 'complaint_rate',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/SES',
                            'MetricName': 'Reputation.ComplaintRate'
                        },
                        'Period': period,
                        'Stat': 'Average'
                    },
                    'Label': 'Complaint Rate',
                    'ReturnData': True
                }
            ],
            'StartTime': current_time - timedelta(seconds=period_timedelta),
            'EndTime': current_time
        }

    def build_ses_account_reputation_metrics(self, metric_data):
        thresholds = self.ses_thresholds

        results = SesReputationMetrics(critical=[],
                                       ok=[],
                                       warning=[])

        for metric in metric_data:
            last_metric = self._get_last_metric(metric)
            critical_threshold = thresholds[THRESHOLD_CRITICAL][metric['Id']]
            warning_threshold = thresholds[THRESHOLD_WARNING][metric['Id']]

            if last_metric:
                label, current_value, metric_ts = last_metric

                if current_value >= critical_threshold:
                    results.critical.append(last_metric)
                elif current_value >= warning_threshold:
                    results.warning.append(last_metric)
                else:
                    results.ok.append(last_metric)

        return results

    def _get_last_metric(self, metric):
        if not metric['Timestamps']:
            return None

        last_ts = max(metric['Timestamps'])
        last_index = metric['Timestamps'].index(last_ts)
        last_value = metric['Values'][last_index]

        return (metric['Label'], last_value * 100.0, str(last_ts))

    def _set_client(self, client):
        if client:
            self._client = client
        else:
            session = boto3.Session(**self._session_config)
            self._client = session.client('cloudwatch')

    def _set_logger(self, logger):
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(self.__module__)
            self._logger.addHandler(logging.NullHandler())

    def _log_get_ses_account_reputation_metrics_request(self, params):
        self.logger.debug('Requesting SES reputation metric data for account')

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name__,
                                    method_name='get_ses_account_reputation_metrics',
                                    params=params))

    def _log_get_ses_account_reputation_metrics_response(self, response):
        self.logger.debug('Received SES reputation metric data for account')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='get_ses_account_reputation_metrics',
                                     response=response))
