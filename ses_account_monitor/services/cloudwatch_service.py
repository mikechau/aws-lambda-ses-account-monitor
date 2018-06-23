# -*- coding: utf-8 -*-

'''
ses_account_monitor.services.cloudwatch_service
~~~~~~~~~~~~~~~~

CloudWatch service module.
'''

import logging

from collections import namedtuple

from datetime import (
    timedelta,
    timezone)

import boto3

from ses_account_monitor.config import (
    LAMBDA_AWS_SESSION_CONFIG,
    SES_REPUTATION_PERIOD,
    SES_REPUTATION_METRIC_TIMEDELTA,
    SES_THRESHOLDS,
    THRESHOLD_CRITICAL,
    THRESHOLD_WARNING)
from ses_account_monitor.util import (
    current_datetime,
    json_dump_request_event,
    json_dump_response_event)


SesReputationMetrics = namedtuple('SesReputationMetrics', ('critical',
                                                           'ok',
                                                           'warning'))
'''
class:SesReputationMetrics

Args:
    critical (:obj:`list` of :obj:`tuple`): List of critical metrics.
    ok (:obj:`list` of :obj:`tuple`): List of ok metrics.
    warning (:obj:`list` of :obj:`tuple`): List of warning metrics.
'''


def build_client(session_config=None):
    '''
    Build a CloudWatch client, if a session config is provided, it will use it to create the client.

    Args:
        session_config (dict):
            aws_access_key_id (str): AWS access key ID.
            aws_secret_access_key (str): AWS secret access key.
            aws_session_token (str): AWS temporary session token.
            region_name (str): Default region when creating new connections.
            botocore_session (botocore.session.Session): Use this Botocore session instead of creating a new default one.
            profile_name (str): The name of a profile to use. If not given, then the default profile is used.

    Returns:
        obj (botocore.client.CloudWatch): The CloudWatch client.
    '''

    if session_config:
        session = boto3.Session(**session_config)
    else:
        session = boto3.Session(**LAMBDA_AWS_SESSION_CONFIG)

    return session.client('cloudwatch')


def get_last_metric(metric):
    '''
    Get last metric from MetricDataResults.

    Args:
        metric (dict):
            Id (str): Metric id.
            Label (str): Metric label.
            StatusCode (str): Status code.
            Timestamps (:obj:`list` of :obj:`datetime`): List of datetime objects.
            Values (:obj:`list` of :obj:`float`): List of floats.

    Returns:
        tuple:
            label (str): The metric label.
            value (float): The metric value.
            iso8601_timestamp (str): ISO 8601 formatted timestamp string.
    '''

    if not metric['Timestamps']:
        return None

    last_ts = max(metric['Timestamps'])
    last_index = metric['Timestamps'].index(last_ts)
    last_value = metric['Values'][last_index]

    return (metric['Label'], last_value, last_ts.astimezone(timezone.utc).isoformat())


class CloudWatchService(object):
    '''
    CloudWatch Service class, interfaces with CloudWatch.
    '''

    def __init__(self,
                 client=None,
                 logger=None,
                 session_config=None,
                 ses_thresholds=None,
                 ses_reputation_period=None,
                 ses_reputation_metric_timedelta=None):
        '''
        Args:
            client (botocore.client.CloudWatch): The CloudWatch client.
            logger (:obj:`logging.Logger`, optional): Logger instance. Defaults to None, which will create a logger instance.
            session_config (:obj:`dict`, optional): The CloudWatch session, used to configure the client if the client is not provided.
            ses_thresholds (:obj:`dict`, optional): SES thresholds configuration.
            ses_reputation_period (:obj:`int`, optional): SES reputation period in seconds.
            ses_reputation_metric_timedelta (:obj:`int`, optional): SES reputation metric timedelta in seconds.
        '''

        self._client = (client or build_client(session_config))
        self._logger = (logger or self._build_logger())

        self.ses_thresholds = (ses_thresholds or SES_THRESHOLDS)
        self.ses_reputation_period = (ses_reputation_period or SES_REPUTATION_PERIOD)
        self.ses_reputation_metric_timedelta = (ses_reputation_metric_timedelta or SES_REPUTATION_METRIC_TIMEDELTA)

    @property
    def client(self):
        '''
        obj (botocore.client.CloudWatch): The CloudWatch client.
        '''

        return self._client

    @property
    def logger(self):
        '''
        obj (logger.Logger): The logger instance.
        '''

        return self._logger

    def get_ses_account_reputation_metrics(self, target_datetime=None, period=None, metric_timedelta=None):
        '''
        Get SES account reputation metrics, fetches it from AWS and then returns the latest metrics in a standardized format.

        Args:
            target_datetime (:obj:`datetime`, optional): The datetime of when to collect reputation metrics from.
                Defaults to None, which will cause the current datetime to be used.
            period (:obj:`int`, optional): The amount of seconds for the measurement periods in CloudWatch.
                Defaults to None, which will use the value set in the config.
            metric_timedelta (:obj:`int`, optional): The amount of seconds for how far back to retrieve metrics from
                the target_datetime. Defaults to None, which will use the value set in the config.

        Returns:
            list (tuple): Returns a list of tuples, representing the reputation metrics.
                label (str): Name of the metric, taken from the CloudWatch metric results data label.
                value (float): The value of the metric, will already be in percentage form.
                threshold (float): The threshold percentage.
                metric_ts (str): ISO 8601 timestamp.
        '''

        if metric_timedelta is None:
            metric_timedelta = self.ses_reputation_metric_timedelta

        metric_data = self.get_ses_account_reputation_metric_data(target_datetime=target_datetime,
                                                                  period=period,
                                                                  metric_timedelta=metric_timedelta)

        return self.build_ses_account_reputation_metrics(metric_data)

    def get_ses_account_reputation_metric_data(self, target_datetime=None, period=None, metric_timedelta=None):
        '''
        Fetch SES account reputation metric data from AWS.

        Args:
            target_datetime (:obj:`datetime`, optional): The datetime of when to collect reputation metrics from.
                Defaults to None, which will cause the current datetime to be used.
            period (:obj:`int`, optional): The amount of seconds for the measurement periods in CloudWatch.
                Defaults to None, which will use the value set in the config.
            metric_timedelta (:obj:`int`, optional): The amount of seconds for how far back to retrieve metrics from
                the target_datetime. Defaults to None, which will use the value set in the config.

        Returns:
            list (dict):
                Id (str): Metric id.
                Label (str): Metric label.
                StatusCode (str): Status code.
                Timestamps (:obj:`list` of :obj:`datetime.datetime`): List of datetime objects.
                Values (:obj:`list` of :obj:`float`): List of floats.
        '''

        self.logger.debug('Fetching SES account reputation metrics...')

        params = self.build_ses_account_reputation_metric_params(
            target_datetime=target_datetime,
            period=period,
            metric_timedelta=metric_timedelta)

        self._log_get_ses_account_reputation_metrics_request(params)

        response = self.client.get_metric_data(**params)

        self._log_get_ses_account_reputation_metrics_response(response)

        return response['MetricDataResults']

    def build_ses_account_reputation_metric_params(self, target_datetime=None, period=None, metric_timedelta=None):
        '''
        Generates params to request SES account reputation metrics.

        Args:
            target_datetime (:obj:`datetime`, optional): The datetime of when to collect reputation metrics from.
                Defaults to None, which will cause the current datetime to be used.
            period (:obj:`int`, optional): The amount of seconds for the measurement periods in CloudWatch.
                Defaults to None, which will use the value set in the config.
            metric_timedelta (:obj:`int`, optional): The amount of seconds for how far back to retrieve metrics from
                the target_datetime. Defaults to None, which will use the value set in the config.

        Returns:
            dict:
                MetricDataQueries (:obj:`list` of :obj:`dict`): List of dict objects, describing the metrics to collect.
                StartTime (datetime): The starting datetime for the metrics collection.
                EndTime (datetime): The ending datetime for the metrics collection.
        '''

        if period is None:
            period = self.ses_reputation_period

        if metric_timedelta is None:
            metric_timedelta = self.ses_reputation_metric_timedelta

        if target_datetime is None:
            target_datetime = current_datetime()

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
            'StartTime': target_datetime - timedelta(seconds=metric_timedelta),
            'EndTime': target_datetime
        }

    def build_ses_account_reputation_metrics(self, metric_data):
        '''
        Formats the account reputation metrics from CloudWatch, returns the most current metrics.

        Args:
            metric_data (:obj:`list` of :obj:`dict`): MetricDataResults from CloudWatch GetMetricData API call.

        Returns:
            list (tuple): Returns a list of tuples, representing the reputation metrics.
                label (str): Name of the metric, taken from the CloudWatch metric results data label.
                value (float): The value of the metric, will already be in percentage form.
                threshold (float): The threshold percentage.
                metric_ts (str): ISO 8601 timestamp.
        '''

        thresholds = self.ses_thresholds

        results = SesReputationMetrics(critical=[],
                                       ok=[],
                                       warning=[])

        for metric in metric_data:
            last_metric = get_last_metric(metric)
            critical_threshold = thresholds[THRESHOLD_CRITICAL][metric['Id']]
            warning_threshold = thresholds[THRESHOLD_WARNING][metric['Id']]

            if last_metric:
                label, current_value, metric_ts = last_metric

                if current_value >= critical_threshold:
                    results.critical.append((label, current_value, critical_threshold, metric_ts))
                elif current_value >= warning_threshold:
                    results.warning.append((label, current_value, warning_threshold, metric_ts))
                else:
                    results.ok.append((label, current_value, warning_threshold, metric_ts))

        return results

    def _build_logger(self):
        '''
        Builds a logger instance.

        Returns:
            obj (logging.Logger): The Logger instance.
        '''

        logger = logging.getLogger(self.__module__)
        logger.addHandler(logging.NullHandler())
        return logger

    def _log_get_ses_account_reputation_metrics_request(self, params):
        '''
        Log the params used to get SES account reputation metrics.

        Args:
            params (dict): MetricDataQueries dict object.
        '''

        self.logger.debug('Requesting SES reputation metric data for account')

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name__,
                                    method_name='get_ses_account_reputation_metrics',
                                    params=params))

    def _log_get_ses_account_reputation_metrics_response(self, response):
        '''
        Log the response from getting SES account reputation metrics.

        Args:
            response (dict): MetricDataResults dict object.
        '''

        self.logger.debug('Received SES reputation metric data for account')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='get_ses_account_reputation_metrics',
                                     response=response))
