# -*- coding: utf-8 -*-

import logging

from datetime import (
    datetime,
    timedelta)

import boto3

from ses_account_monitor.config import (
    SES_REPUTATION_PERIOD,
    SES_REPUTATION_PERIOD_TIMEDELTA)
from ses_account_monitor.util import (
    json_dump_request_event,
    json_dump_response_event)


class CloudWatchClient(object):
    def __init__(self,
                 client=None,
                 reputation_config=None,
                 logger=None,
                 session_config=None):
        self._session_config = session_config
        self._set_client(client)
        self._set_reputation_config(reputation_config)
        self._set_logger(logger)

    @property
    def client(self):
        return self._client

    @property
    def logger(self):
        return self._logger

    def get_ses_reputation_metrics(self, current_time=None, period=None, period_timedelta=None):
        params = self.get_ses_reputation_metric_params(
            current_time=current_time,
            period=period,
            period_timedelta=period_timedelta)

        self._log_get_ses_reputation_metrics_request(params)

        response = self.client.get_metric_data(**params)

        self._log_get_ses_reputation_metrics_response(response)

        return response['MetricDataResults']

    def get_ses_reputation_metric_params(self, current_time=None, period=None, period_timedelta=None):
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
                    'Label': 'bounce_rate',
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
                    'Label': 'complaint_rate',
                    'ReturnData': True
                }
            ],
            'StartTime': current_time - timedelta(seconds=period_timedelta),
            'EndTime': current_time
        }

    def _set_client(self, client):
        if client:
            self._client = client
        else:
            self._client = self._build_cloudwatch_client()

    def _set_reputation_config(self, reputation_config):
        if reputation_config:
            self.ses_reptuation_period = reputation_config['ses_reputation_period']
            self.ses_reputation_period_timedelta = reputation_config['ses_reputation_period_timedelta']
        else:
            self.ses_reputation_period = SES_REPUTATION_PERIOD
            self.ses_reputation_period_timedelta = SES_REPUTATION_PERIOD_TIMEDELTA

    def _set_logger(self, logger):
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(self.__module__)
            self._logger.addHandler(logging.NullHandler())

    def _build_cloudwatch_client(self):
        session_config = self._session_config

        if session_config:
            session = boto3.Session(**session_config)
            client = session.client('cloudwatch')
        else:
            client = boto3.client('cloudwatch')

        return client

    def _log_get_ses_reputation_metrics_request(self, params):
        self.logger.debug('Requesting SES reputation metric data for account')

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name__,
                                    method_name='get_ses_reputation_metrics',
                                    params=params))

    def _log_get_ses_reputation_metrics_response(self, response):
        self.logger.debug('Received SES reputation metric data for account')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='get_ses_reputation_metrics',
                                     response=response))
