# -*- coding: utf-8 -*-
import logging

from ses_account_monitor.services import (
    PagerDutyService,
    SesService,
    SlackService)

from ses_account_monitor.config import (
    NOTIFY_CONFIG,
    NOTIFY_STRATEGY_LIVE,
    NOTIFY_STRATEGY_SIMULATION,
    SES_SENDING_QUOTA_WARNING_PERCENT,
    SES_SENDING_QUOTA_CRITICAL_PERCENT,
    THRESHOLD_CRITICAL,
    THRESHOLD_OK,
    THRESHOLD_WARNING)

from ses_account_monitor.util import (
    json_dump_request_event,
    json_dump_response_event)

THRESHOLDS = {
    'ses_sending_quota_warning_percent': SES_SENDING_QUOTA_WARNING_PERCENT,
    'ses_sending_quota_critical_percent': SES_SENDING_QUOTA_CRITICAL_PERCENT
}


class Monitor(object):
    def __init__(self, aws_config=None,  notify_config=False, thresholds=None, ses_service=None, slack_service=None, pager_duty_service=None, logger=None):
        self._notify_config = (notify_config or NOTIFY_CONFIG)
        self._thresholds = (thresholds or THRESHOLDS)

        self.ses_service = (ses_service or SesService())
        self.pager_duty_service = (pager_duty_service or PagerDutyService())
        self.slack_service = (slack_service or SlackService())

        self._set_logger(logger)

    @property
    def ses_service(self):
        return self._ses_service

    @property
    def ses_sending_quota_warning_percent(self):
        return self._thresholds['ses_sending_quota_warning_percent']

    @property
    def ses_sending_quota_critical_percent(self):
        return self._thresholds['ses_sending_quota_critical_percent']

    @property
    def logger(self):
        return self._logger

    @property
    def notify_config(self):
        return self._notify_config

    def handle_ses_quota(self):
        current_percent = self.ses_service.get_account_sending_current_percentage()
        critical_percent = self.ses_service.ses_sending_quota_critical_percent()
        warning_percent = self.ses_service.ses_sending_quota_warning_percent()

        if current_percent >= critical_percent:
            self._log_handle_ses_quota_request(current_percent, critical_percent, 'CRITICAL')
            self._log_handle_ses_quota_response(current_percent, critical_percent, 'CRITICAL')
        elif current_percent >= warning_percent:
            self._log_handle_ses_quota_request(current_percent, critical_percent, 'WARNING')
            self._log_handle_ses_quota_response(current_percent, critical_percent, 'WARNING')
        else:
            self._log_handle_ses_quota_response(current_percent, critical_percent, 'OK')

    def _set_logger(self, logger):
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(self.__module__)
            self._logger.addHandler(logging.NullHandler())

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
            json_dump_response_event(class_name=self.__class__.__name,
                                     method_name='handle_ses_quota',
                                     details={
                                         'current_percent': current_percent,
                                         'threshold_percent': threshold_percent,
                                         'status': status
                                     }))
