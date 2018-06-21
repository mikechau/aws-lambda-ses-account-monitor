# -*- coding: utf-8 -*-

'''
ses_account_monitor.services.ses_service
~~~~~~~~~~~~~~~~

SES service module.
'''

from __future__ import division

import logging

import boto3

from ses_account_monitor.config import LAMBDA_AWS_SESSION_CONFIG

from ses_account_monitor.util import (
    iso8601_timestamp,
    json_dump_request_event,
    json_dump_response_event)


class SesService(object):
    '''
    SES Service class, interfaces with SES.
    '''

    def __init__(self,
                 client=None,
                 logger=None,
                 session_config=None):
        '''
        Args:
            client (botocore.client.SES): The SES client.
            logger (:obj:`logging.Logger`, optional): Logger instance. Defaults to None, which will create a logger instance.
            session_config (:obj:`dict`, optional): The SES session, used to configure the client if the client is not provided.
        '''

        self._client = (client or self._build_client(session_config))
        self._logger = (logger or self._build_logger())

    @property
    def client(self):
        '''
        obj (botocore.client.SES): The SES client.
        '''

        return self._client

    @property
    def logger(self):
        '''
        obj (logger.Logger): The logger instance.
        '''

        return self._logger

    def get_account_sending_stats(self, event_iso_ts=None):
        '''
        Get account sending stats, fetches it from AWS and then returns the latest metrics in a standardized format.

        Args:
            event_iso_ts (:obj:`str`, optional): ISO 8601 formatted timestamp string.
                Default is None, which will cause the current date to be used.

        Returns:
            tuple: Tuple containing the metric statistics.
                volume (float): The total number of emails sent.
                max_volume (float): The max number of emails allowed to be sent.
                usage (float): Percentage of max_volume being utilized, 80% is represented as 80.
                ts (str): ISO 8601 formatted timestamp string.
        '''

        ts = (event_iso_ts or iso8601_timestamp())
        stats = self.get_account_sending_quota()
        volume = stats['SentLast24Hours']
        max_volume = stats['Max24HourSend']
        usage = self._get_utilization_percentage(volume, max_volume)
        return (volume, max_volume, usage, ts)

    def get_account_sending_quota(self):
        '''
        Fetch the account sending quota from AWS.

        Returns:
            dict: AWS SES sending quota response.
                Max24HourSend (float): Max number of emails allowed to send in a 24 hour interval.
                MaxSendRate (float): Max send rate.
                SentLast24Hours (float): Emails sent in the last 24 hours.
        '''

        return self.client.get_send_quota()

    def get_account_sending_current_percentage(self):
        '''
        Get the utilization percentage of the account email sending quota.

        Returns:
            float: A float representing the percentage. Ex: 80% is 80.
        '''

        stats = self.get_account_sending_quota()
        usage = self._get_utilization_percentage(stats['SentLast24Hours'], stats['Max24HourSend'])
        return usage

    def get_account_sending_remaining_percentage(self):
        '''
        Get the remaining percentage of the account email sending quota.

        Returns:
            float: A float representing the percentage. Ex: 80% is 80.
        '''

        current_percentage = self.get_account_sending_current_percentage()

        remaining = 100 - current_percentage

        if remaining <= 0:
            return 0

        return remaining

    def is_account_sending_rate_over(self, percent=None):
        '''
        Check if the account sending rate is over a percentage limit.

        Args:
            percent (:obj:`float/int`, optional): A float or int representing the percentage. Ex: 80% is 80.
                Default is None, and assumes 100.

        Returns:
            bool: True if the account sending rate is over, False if not.
        '''

        if percent is None:
            percent = 100

        stats = self.get_account_sending_quota()

        threshold = (percent * stats['Max24HourSend']) / 100.0

        return stats['SentLast24Hours'] >= threshold

    def is_account_sending_enabled(self):
        '''
        Check if account sending is enabled.

        Returns:
            bool: True if account sending is enabled, False if disabled.
        '''

        return self.client.get_account_sending_enabled()['Enabled']

    def toggle_account_sending(self):
        '''
        Toggle account sending.

        Returns:
            bool: True is account sending is enabled, False if disabled.
        '''

        if self.is_account_sending_enabled():
            self.logger.debug('SES account sending is currently ENABLED, transitioning to DISABLED.')

            return self.disable_account_sending()
        else:
            self.logger.debug('SES account sending is currently DISABLED, transitioning to ENABLED.')

            return self.enable_account_sending()

    def enable_account_sending(self):
        '''
        Enable account sending.

        Returns:
            bool: True, for when account sending is enabled.
        '''

        self._log_enable_account_sending_request()

        self.client.update_account_sending_enabled(Enabled=True)

        self._log_enable_account_sending_response()

        return True

    def disable_account_sending(self):
        '''
        Disable account sending.

        Returns:
            bool: False, for when account sending is disabled.
        '''

        self._log_disable_account_sending_request()

        self.client.update_account_sending_enabled(Enabled=False)

        self._log_disable_account_sending_response()

        return False

    def _build_client(self, session_config):
        '''
        Build a SES client, if a session config is provided, it will use it to create the client.

        Args:
            session_config (dict):
                aws_access_key_id (str): AWS access key ID.
                aws_secret_access_key (str): AWS secret access key.
                aws_session_token (str): AWS temporary session token.
                region_name (str): Default region when creating new connections.
                botocore_session (botocore.session.Session): Use this Botocore session instead of creating a new default one.
                profile_name (str): The name of a profile to use. If not given, then the default profile is used.

        Returns:
            obj (botocore.client.SES): The SES client.
        '''

        if session_config:
            session = boto3.SesService(**session_config)
        else:
            session = boto3.Session(**LAMBDA_AWS_SESSION_CONFIG)
        return session.client('ses')

    def _build_logger(self):
        '''
        Builds a logger instance.

        Returns:
            obj (logging.Logger): The Logger instance.
        '''

        logger = logging.getLogger(self.__module__)
        logger.addHandler(logging.NullHandler())
        return logger

    def _get_utilization_percentage(self, current, total):
        '''
        Calculate the utilization percentage.

        Args:
            current (float/int): The current amount.
            total (float/int): The total amount.

        Returns:
            float: The utilization percentage.
        '''

        return ((current / total) * 100.0)

    def _log_enable_account_sending_request(self):
        '''
        Log the enable account sending request.
        '''

        self.logger.debug('Preparing to enable SES account sending...')

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name__,
                                    method_name='enable_account_sending_request'))

    def _log_enable_account_sending_response(self):
        '''
        Log the enable account sending response.
        '''

        self.logger.debug('SES account sending ENABLED!')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='enable_account_sending_request'))

    def _log_disable_account_sending_request(self):
        '''
        Log the disable account sending request.
        '''

        self.logger.debug('Preparing to disable SES account sending...')

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name__,
                                    method_name='disable_account_sending_request'))

    def _log_disable_account_sending_response(self):
        '''
        Log the disable account sending response.
        '''

        self.logger.debug('SES account sending DISABLED!')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='disable_account_sending_request'))
