# -*- coding: utf-8 -*-
from __future__ import division

import logging

import boto3

from ses_account_monitor.util import (
    json_dump_request_event,
    json_dump_response_event)


class SesClient(object):
    def __init__(self,
                 client=None,
                 logger=None,
                 session_config=None):

        self._session_config = session_config
        self._set_client(client)
        self._set_logger(logger)

    @property
    def client(self):
        return self._client

    @property
    def logger(self):
        return self._logger

    def get_account_sending_quota(self):
        return self.client.get_send_quota()

    def get_account_sending_current_percentage(self):
        stats = self.get_account_sending_quota()

        usage = ((stats['SentLast24Hours'] / stats['Max24HourSend']) * 100)

        if usage >= 100:
            return 100

        return usage

    def get_account_sending_remaining_percentage(self):
        current_percentage = self.get_account_sending_current_percentage()

        remaining = 100 - current_percentage

        if remaining <= 0:
            return 0

        return remaining

    def is_account_sending_rate_over(self, percent=None):
        if percent is None:
            percent = 100

        stats = self.get_account_sending_quota()

        threshold = (percent * stats['Max24HourSend']) / 100.0

        return stats['SentLast24Hours'] >= threshold

    def is_account_sending_enabled(self):
        return self.client.get_account_sending_enabled()['Enabled']

    def toggle_account_sending(self):
        if self.is_account_sending_enabled():
            self.logger.debug('SES account sending is currently ENABLED, transitioning to DISABLED.')

            return self.disable_account_sending()
        else:
            self.logger.debug('SES account sending is currently DISABLED, transitioning to ENABLED.')

            return self.enable_account_sending()

    def enable_account_sending(self):
        self._log_enable_account_sending_request()

        self.client.update_account_sending_enabled(Enabled=True)

        self._log_enable_account_sending_response()

        return True

    def disable_account_sending(self):
        self._log_disable_account_sending_request()

        self.client.update_account_sending_enabled(Enabled=False)

        self._log_disable_account_sending_response()

        return False

    def _set_client(self, client):
        if client:
            self._client = client
        else:
            self._client = self._build_ses_client()

    def _set_logger(self, logger):
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(self.__module__)
            self._logger.addHandler(logging.NullHandler())

    def _build_ses_client(self):
        session_config = self._session_config

        if session_config:
            session = boto3.Session(**session_config)
            client = session.client('ses')
        else:
            client = boto3.client('ses')

        return client

    def _log_enable_account_sending_request(self):
        self.logger.debug('Preparing to enable SES account sending...')

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name__,
                                    method_name='enable_account_sending_request'))

    def _log_enable_account_sending_response(self):
        self.logger.debug('SES account sending ENABLED!')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='enable_account_sending_request'))

    def _log_disable_account_sending_request(self):
        self.logger.debug('Preparing to disable SES account sending...')

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name__,
                                    method_name='disable_account_sending_request'))

    def _log_disable_account_sending_response(self):
        self.logger.debug('SES account sending DISABLED!')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='disable_account_sending_request'))
