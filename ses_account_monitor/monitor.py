# -*- coding: utf-8 -*-
import logging

from ses_account_monitor.services import (
    CloudWatchService,
    PagerDutyService,
    SesService,
    SlackService)

from ses_account_monitor.config import (
    ACTION_DISABLE,
    ACTION_ALERT,
    ACTION_ENABLE,
    NOTIFY_CONFIG,
    SES_MANAGEMENT_STRATEGY,
    SES_STRATEGY_ALERT,
    SES_STRATEGY_MANAGED,
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
    def __init__(self,
                 ses_management_strategy=None,
                 aws_config=None,
                 notify_config=False,
                 thresholds=None,
                 cloudwatch_service=None,
                 ses_service=None,
                 slack_service=None,
                 pager_duty_service=None,
                 logger=None):
        self._notify_config = (notify_config or NOTIFY_CONFIG)
        self._thresholds = (thresholds or THRESHOLDS)

        self.ses_management_strategy = (ses_management_strategy or SES_MANAGEMENT_STRATEGY)
        self.ses_service = (ses_service or SesService())
        self.cloudwatch_service = (cloudwatch_service or CloudWatchService())
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

    def send_notifications(self):
        self.logger.debug('Sending notifications...')
        self.pager_duty_service.send_notifications()
        self.slack_service.send_notifications()
        self.logger.debug('Finished sending all notifications!')

    def handle_ses_sending_quota(self, current_time=None):
        self.logger.debug('Handling SES account sending quota...')

        if self.ses_management_strategy != SES_STRATEGY_MANAGED or self.ses_management_strategy != SES_STRATEGY_ALERT:
            self.logger.debug('SES management strategy %s is not VALID, skipping!', self.ses_management_strategy)
            return

        volume, max_volume, utilization_percent, metric_ts = self.ses_service.get_account_sending_stats(current_time)

        critical_percent = self.ses_sending_quota_critical_percent
        warning_percent = self.ses_sending_quota_warning_percent

        if utilization_percent >= critical_percent:
            self._handle_ses_sending_quota_critical(utilization_percent=utilization_percent,
                                                    critical_percent=critical_percent,
                                                    volume=volume,
                                                    max_volume=max_volume,
                                                    metric_ts=metric_ts)
        elif utilization_percent >= warning_percent:
            self._handle_ses_sending_quota_warning(utilization_percent=utilization_percent,
                                                   warning_percent=warning_percent,
                                                   volume=volume,
                                                   max_volume=max_volume,
                                                   metric_ts=metric_ts)
        else:
            self._handle_ses_sending_quota_ok(utilization_percent=utilization_percent,
                                              warning_percent=warning_percent)

    def handle_ses_reputation(self, current_time=None, period=None, period_timedelta=None):
        self.logger.debug('Handling SES account reputation...')

        if self.ses_management_strategy != SES_STRATEGY_MANAGED or self.ses_management_strategy != SES_STRATEGY_ALERT:
            self.logger.debug('SES management strategy %s is not VALID, skipping!', self.ses_management_strategy)
            return

        metrics = self.cloudwatch_service.get_ses_account_reputation_metrics(current_time=current_time,
                                                                             period=period,
                                                                             period_timedelta=period_timedelta)

        if metrics.critical:
            self._handle_ses_reputation_critical(metrics=metrics,
                                                 current_time=current_time)
        elif metrics.warning:
            self._handle_ses_reputation_warning(metrics=metrics,
                                                current_time=current_time)
        elif metrics.ok:
            self._handle_ses_reputation_ok(metrics=metrics,
                                           current_time=current_time)

    def _set_logger(self, logger):
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(self.__module__)
            self._logger.addHandler(logging.NullHandler())

    def _handle_ses_sending_quota_critical(self, utilization_percent, critical_percent, volume, max_volume, metric_ts):
        self.logger.debug('SES sending quota is in a CRITICAL state!')
        self._log_handle_ses_quota_request(utilization_percent, critical_percent, 'CRITICAL')

        if self.notify_config.notify_pager_duty_on_ses_sending_quota:
            self.logger.debug('Pager Duty alerting is ENABLED, queuing TRIGGER event...')
            self.pager_duty_service.enqueue_ses_account_sending_quota_trigger_event(volume=volume,
                                                                                    max_volume=max_volume,
                                                                                    utilization_percent=utilization_percent,
                                                                                    threshold_percent=critical_percent,
                                                                                    metric_ts=metric_ts)
        else:
            self.logger.debug('Pager Duty alerting is DISABLED, skipping...')

        if self.notify_config.notify_slack_on_ses_sending_quota:
            self.logger.debug('Slack notifications is ENABLED, queuing message...')

            self.slack_service.enqueue_ses_account_sending_quota_message(threshold_name=THRESHOLD_CRITICAL,
                                                                         utilization_percent=utilization_percent,
                                                                         threshold_percent=critical_percent,
                                                                         volume=volume,
                                                                         max_volume=max_volume,
                                                                         metric_ts=metric_ts)
        else:
            self.logger.debug('Slack notifications is DISABLED, skipping...')

        self._log_handle_ses_quota_response()

    def _handle_ses_sending_quota_warning(self, utilization_percent, warning_percent, volume, max_volume, metric_ts):
        self.logger.debug('SES sending quota is in a WARNING state!')

        self._log_handle_ses_quota_request(utilization_percent, warning_percent, 'WARNING')

        if self.notify_config.notify_pager_duty_on_ses_sending_quota:
            self.logger.debug('Pager Duty alerting is ENABLED, queuing RESOLVE event...')
            self.pager_duty_service.enqueue_ses_account_sending_quota_resolve_event()
        else:
            self.logger.debug('Pager Duty alerting is DISABLED, skipping...')

        if self.notify_config.notify_slack_on_ses_sending_quota:
            self.logger.debug('Slack notifications is ENABLED, queuing message...')

            self.slack_service.enqueue_ses_account_sending_quota_message(threshold_name=THRESHOLD_WARNING,
                                                                         utilization_percent=utilization_percent,
                                                                         threshold_percent=warning_percent,
                                                                         volume=volume,
                                                                         max_volume=max_volume,
                                                                         metric_ts=metric_ts)
        else:
            self.logger.debug('Slack notifications is DISABLED, skipping...')

        self._log_handle_ses_quota_response()

    def _handle_ses_sending_quota_ok(self, utilization_percent, warning_percent):
        self.logger.debug('SES sending quota is in a OK state!')

        self._log_handle_ses_quota_request(utilization_percent, warning_percent, 'OK')

        if self.notify_config.notify_pager_duty_on_ses_sending_quota:
            self.logger.debug('Pager Duty alerting is ENABLED, queuing RESOLVE event...')
            self.pager_duty_service.enqueue_ses_account_sending_quota_resolve_event()
        else:
            self.logger.debug('Pager Duty alerting is DISABLED, skipping...')

        self._log_handle_ses_quota_response()

    def _handle_ses_reputation_critical(self, metrics, current_time=None):
        self.logger.debug('SES account reputation has metrics in a %s state!', THRESHOLD_CRITICAL)

        self._log_handle_ses_reputation_request(metrics=metrics,
                                                status=THRESHOLD_CRITICAL)

        danger_metrics = (metrics.critical + metrics.warning)
        action = ACTION_ALERT

        if self.ses_management_strategy == SES_STRATEGY_MANAGED:
            self.logger.debug('SES management strategy is %s, status is %s, DISABLING...', SES_STRATEGY_MANAGED, THRESHOLD_CRITICAL)
            self.ses_service.disable_account_sending()
            action = ACTION_DISABLE
        else:
            self.logger.debug('SES management strategy is %s, status is %s, skipping...', SES_STRATEGY_MANAGED, THRESHOLD_CRITICAL)

        if self.notify_config.notify_pager_duty_on_ses_reputation:
            self.logger.debug('Pager Duty alerting is ENABLED, queuing TRIGGER event...')
            self.pager_duty_service.enqueue_ses_account_reputation_trigger_event(metrics=danger_metrics,
                                                                                 event_ts=current_time,
                                                                                 metric_ts=current_time,
                                                                                 action=action)
        else:
            self.logger.debug('Pager Duty alerting is DISABLED, skipping...')

        if self.notify_config.notify_slack_on_ses_reputation:
            self.logger.debug('Slack notifications is ENABLED, queuing message...')

            self.slack_service.enqueue_ses_account_reputation_message(threshold_name=THRESHOLD_CRITICAL,
                                                                      metrics=danger_metrics,
                                                                      metric_ts=current_time,
                                                                      action=action)
        else:
            self.logger.debug('Slack notifications is DISABLED, skipping...')

        self._log_handle_ses_reputation_response()

    def _handle_ses_reputation_warning(self, metrics, current_time=None):
        action = ACTION_ALERT

        self.logger.debug('SES account reputation has metrics in a %s state!', THRESHOLD_WARNING)

        self._log_handle_ses_reputation_request(metrics=metrics,
                                                status=THRESHOLD_WARNING)

        if self.ses_management_strategy == SES_STRATEGY_MANAGED:
            self.logger.debug('SES management strategy is %s, status is %s, ENABLING...', SES_STRATEGY_MANAGED, THRESHOLD_WARNING)

            if not self.ses_service.is_account_sending_enabled():
                self.logger.debug('SES account sending is currently DISABLED! ENABLING...')
                self.ses_service.enable_account_sending()

                action = ACTION_ENABLE
        else:
            self.logger.debug('SES management strategy is %s, status is %s, skipping...', SES_STRATEGY_MANAGED, THRESHOLD_CRITICAL)

        if self.notify_config.notify_slack_on_ses_reputation:
            self.logger.debug('Slack notifications is ENABLED, queuing message...')

            self.slack_service.enqueue_ses_account_reputation_message(threshold_name=THRESHOLD_WARNING,
                                                                      metrics=metrics.warning,
                                                                      metric_ts=current_time,
                                                                      action=action)
        else:
            self.logger.debug('Slack notifications is DISABLED, skipping...')

        self._log_handle_ses_reputation_response()

    def _handle_ses_reputation_ok(self, metrics, current_time=None):
        self.logger.debug('SES account reputation has metrics in a %s state!', THRESHOLD_OK)

        self._log_handle_ses_reputation_request(metrics=metrics,
                                                status=THRESHOLD_OK)

        if self.ses_management_strategy == SES_STRATEGY_MANAGED:
            self.logger.debug('SES management strategy is %s, status is %s, ENABLING...', SES_STRATEGY_MANAGED, THRESHOLD_OK)

            if not self.ses_service.is_account_sending_enabled():
                self.logger.debug('SES account sending is currently DISABLED! ENABLING...')
                self.ses_service.enable_account_sending()

                if self.notify_config.notify_slack_on_ses_reputation:
                    self.logger.debug('Slack notifications is ENABLED, queuing message...')

                    self.slack_service.enqueue_ses_account_reputation_message(threshold_name=THRESHOLD_WARNING,
                                                                              metrics=metrics.warning,
                                                                              metric_ts=current_time,
                                                                              action=ACTION_ENABLE)
                else:
                    self.logger.debug('Slack notifications is DISABLED, skipping...')

        else:
            self.logger.debug('SES management strategy is %s, status is %s, skipping...', SES_STRATEGY_MANAGED, THRESHOLD_OK)

        self._log_handle_ses_reputation_response()

    def _log_handle_ses_quota_request(self, utilization_percent, threshold_percent, status):
        self.logger.debug('SES account sending percentage is at %s%, threshold is at %s, status is %s!',
                          utilization_percent,
                          threshold_percent,
                          status)

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name,
                                    method_name='handle_ses_quota',
                                    details={
                                        'utilization_percent': utilization_percent,
                                        'threshold_percent': threshold_percent,
                                        'status': status
                                    }))

    def _log_handle_ses_quota_response(self):
        self.logger.debug('SES account sending handler complete.')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name,
                                     method_name='handle_ses_quota'))

    def _log_handle_ses_reputation_request(self, metrics, status):
        critical_count = len(metrics.critical_count)
        warning_count = len(metrics.warning_count)
        ok_count = len(metrics.ok)

        self.logger.debug('SES account reputation metrics - critical: %s, warning: %s, ok: %s, status is %s!',
                          critical_count,
                          warning_count,
                          ok_count)

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name,
                                    method_name='handle_ses_reputation',
                                    details=metrics))

    def _log_handle_ses_reputation_response(self):
        self.logger.debug('SES account reputation handler complete.')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name,
                                     method_name='handle_ses_reputation'))
