# -*- coding: utf-8 -*-
import logging
from collections import deque

from ses_account_monitor.services import (
    SesService)
from ses_account_monitor.config import (
    LAMBDA_AWS_REGION)
from ses_account_monitor.util import (
    json_dump_request_event,
    json_dump_response_event)


NOTIFY_LIVE_STRATEGY = 'live'
NOTIFY_DEBUG_STRATEGY = 'debug'
NOTIFY_NOOP_STRATEGY = 'noop'

AWS_CONFIG = {
    'session_config': {
        'region_name': LAMBDA_AWS_REGION
    }
}

NOTIFY_CONFIG = {
    'service': {
        'slack': False,
        'pagerduty': False
    },
    'strategy': NOTIFY_LIVE_STRATEGY
}

THRESHOLDS = {
    'SES_SENDING_QUOTA_WARNING_PERCENT': 80,
    'SES_SENDING_QUOTA_CRITICAL_PERCENT': 90
}


class Monitor(object):
    def __init__(self, aws_config=None,  notify_config=False, thresholds=None, ses_service=None, logger=None):
        self._aws_config = (aws_config or AWS_CONFIG)
        self._notify_config = (notify_config or NOTIFY_CONFIG)
        self._thresholds = (thresholds or THRESHOLDS)
        self._message_queue = {
            'slack': deque([]),
            'pagerduty': deque([])
        }

        self._set_ses_service(ses_service)
        self._set_logger(logger)

    @property
    def ses_service(self):
        return self._ses_service

    @property
    def slack_messages(self):
        return self._message_queue['slack']

    @property
    def pagerduty_events(self):
        return self._message_queue['pagerduty']

    @property
    def ses_sending_quota_warning_percent(self):
        return self._thresholds['SES_SENDING_QUOTA_WARNING_PERCENT']

    @property
    def ses_sending_quota_critical_percent(self):
        return self._thresholds['SES_SENDING_QUOTA_CRITICAL_PERCENT']

    @property
    def logger(self):
        return self._logger

    @property
    def notify_strategy(self):
        return self._notify_config['strategy']

    def handle_ses_quota(self):
        current_percent = self.ses_service.get_account_sending_current_percentage()
        critical_percent = self.ses_sending_quota_critical_percent()
        warning_percent = self.ses_sending_quota_warning_percent()

        if current_percent >= critical_percent:
            self._log_handle_ses_quota_request(current_percent, critical_percent, 'CRITICAL')
            self._log_handle_ses_quota_response(current_percent, critical_percent, 'CRITICAL')
        elif current_percent >= warning_percent:
            self._log_handle_ses_quota_request(current_percent, critical_percent, 'WARNING')
            self._log_handle_ses_quota_response(current_percent, critical_percent, 'WARNING')
        else:
            self._log_handle_ses_quota_response(current_percent, critical_percent, 'OK')

    def build_ses_quota_slack_message(self, color):
        return {
            'attachments': [
                {
                    'fallback': 'Send rate has breached warning threshold.',
                    'color': 'warning',
                    'title_link': 'https://console.amazonaws.com/',
                    'fields': [
                        {
                            'title': 'Service',
                            'value': '<https://google.com|SES Account Sending>',
                            'short': True
                        },
                        {
                            'title': 'Account',
                            'value': 'ellation',
                            'short': True
                        },
                        {
                            'title': 'Region',
                            'value': 'us-west-2',
                            'short': True
                        },
                        {
                            'title': 'Environment',
                            'value': 'global',
                            'short': True
                        },
                        {
                            'title': 'Status',
                            'value': 'WARNING',
                            'short': True
                        },
                        {
                            'title': 'Threshold',
                            'value': '60%',
                            'short': True
                        },
                        {
                            'title': 'Current',
                            'value': '60%',
                            'short': True
                        },
                        {
                            'title': 'Sent / Max',
                            'value': '3 / 3',
                            'short': True
                        },
                        {
                            'title': 'Message',
                            'value': 'SES account sending has breached the WARNING threshold.',
                            'short': False
                        }
                    ],
                    'footer': 'ellation-us-west-2-global-ses-account-monitor',
                    'footer_icon': 'https://platform.slack-edge.com/img/default_application_icon.png',
                    'ts': 123456789
                }
            ],
            'username': 'SES Account Monitor'
        }

    def is_slack_notify_enabled(self):
        return self._notify_config['service']['slack']

    def is_pagerduty_notify_enabled(self):
        return self._notify_config['service']['pagerduty']

    def _set_ses_service(self, ses_service):
        if ses_service:
            self._ses_service = ses_service
        else:
            self._ses_service = SesService(**self._aws_config)

    def _set_logger(self, logger):
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(self.__module__)
            self._logger.addHandler(logging.NullHandler())

    def _enqueue_message(self, target, message):
        self._message_queue[target].put(message)

    def _log_handle_ses_quota_request(self, current_percent, threshold_percent, status):
        self.logger.debug('SES account sending percentage is at %s%, threshold is at %s, status is %s!',
                          current_percent,
                          threshold_percent,
                          status)

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name,
                                    method_name='handle_ses_quota',
                                    details={
                                        'current_percent': current_percent,
                                        'threshold_percent': threshold_percent,
                                        'status': status
                                    }))

    def _log_handle_ses_quota_response(self, current_percent, threshold_percent, status):
        self.logger.debug('SES account sending percentage is at %s%, threshold is at %s, status is %s!',
                          current_percent,
                          threshold_percent,
                          status)

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name,
                                    method_name='handle_ses_quota',
                                    details={
                                        'current_percent': current_percent,
                                        'threshold_percent': threshold_percent,
                                        'status': status
                                    }))
