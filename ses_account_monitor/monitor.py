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
    MONITOR_SES_REPUTATION,
    MONITOR_SES_SENDING_QUOTA,
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
    current_datetime,
    iso8601_timestamp,
    unix_timestamp,
    json_dump_request_event,
    json_dump_response_event)

THRESHOLDS = {
    'ses_sending_quota_warning_percent': SES_SENDING_QUOTA_WARNING_PERCENT,
    'ses_sending_quota_critical_percent': SES_SENDING_QUOTA_CRITICAL_PERCENT
}


class NotificationFailure(Exception):
    pass


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
                 monitor_ses_reputation=MONITOR_SES_REPUTATION,
                 monitor_ses_sending_quota=MONITOR_SES_SENDING_QUOTA,
                 logger=None):
        self._notify_config = (notify_config or NOTIFY_CONFIG)
        self._thresholds = (thresholds or THRESHOLDS)

        self.monitor_ses_reputation = monitor_ses_reputation
        self.monitor_ses_sending_quota = monitor_ses_sending_quota
        self.ses_management_strategy = (ses_management_strategy or SES_MANAGEMENT_STRATEGY)
        self.ses_service = (ses_service or SesService())
        self.cloudwatch_service = (cloudwatch_service or CloudWatchService())
        self.pager_duty_service = (pager_duty_service or PagerDutyService())
        self.slack_service = (slack_service or SlackService())

        self._set_logger(logger)

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

    def send_notifications(self, raise_on_errors=False):
        self.logger.debug('Sending notifications...')
        self.pager_duty_service.send_notifications()
        self.slack_service.send_notifications()
        self.logger.debug('Finished sending all notifications!')

        if raise_on_errors:
            self._handle_notification_responses()

        return self._get_notification_responses()

    def handle_ses_sending_quota(self, target_datetime=None):
        if not self.monitor_ses_sending_quota:
            self.logger.debug('Handling SES account sending quota is DISABLED, skipping...')
            return

        self.logger.debug('Handling SES account sending quota...')

        if (self.ses_management_strategy != SES_STRATEGY_MANAGED) and (self.ses_management_strategy != SES_STRATEGY_ALERT):
            self.logger.debug('SES management strategy %s is not VALID, skipping!', self.ses_management_strategy)
            return

        target_datetime = (target_datetime or current_datetime())
        event_iso_ts = iso8601_timestamp(target_datetime)
        event_unix_ts = unix_timestamp(target_datetime)

        volume, max_volume, utilization_percent, metric_iso_ts = self.ses_service.get_account_sending_stats(event_iso_ts=event_iso_ts)

        critical_percent = self.ses_sending_quota_critical_percent
        warning_percent = self.ses_sending_quota_warning_percent

        if utilization_percent >= critical_percent:
            self._handle_ses_sending_quota_critical(utilization_percent=utilization_percent,
                                                    critical_percent=critical_percent,
                                                    volume=volume,
                                                    max_volume=max_volume,
                                                    metric_iso_ts=metric_iso_ts,
                                                    event_iso_ts=event_iso_ts,
                                                    event_unix_ts=event_unix_ts)
        elif utilization_percent >= warning_percent:
            self._handle_ses_sending_quota_warning(utilization_percent=utilization_percent,
                                                   warning_percent=warning_percent,
                                                   volume=volume,
                                                   max_volume=max_volume,
                                                   metric_iso_ts=metric_iso_ts,
                                                   event_unix_ts=event_unix_ts)
        else:
            self._handle_ses_sending_quota_ok(utilization_percent=utilization_percent,
                                              warning_percent=warning_percent)

        return self._get_pending_notifications()

    def handle_ses_reputation(self, target_datetime=None, period=None, period_timedelta=None):
        if not self.monitor_ses_reputation:
            self.logger.debug('Handling SES reputation is DISABLED, skipping...')
            return

        self.logger.debug('Handling SES account reputation...')

        if (self.ses_management_strategy != SES_STRATEGY_MANAGED) and (self.ses_management_strategy != SES_STRATEGY_ALERT):
            self.logger.debug('SES management strategy %s is not VALID, skipping!', self.ses_management_strategy)
            return

        target_datetime = (target_datetime or current_datetime())
        event_iso_ts = iso8601_timestamp(target_datetime)
        event_unix_ts = unix_timestamp(target_datetime)

        metrics = self.cloudwatch_service.get_ses_account_reputation_metrics(target_datetime=target_datetime,
                                                                             period=period,
                                                                             period_timedelta=period_timedelta)

        if metrics.critical:
            self._handle_ses_reputation_critical(metrics=metrics,
                                                 event_iso_ts=event_iso_ts,
                                                 event_unix_ts=event_unix_ts)
        elif metrics.warning:
            self._handle_ses_reputation_warning(metrics=metrics,
                                                event_unix_ts=event_unix_ts)
        elif metrics.ok:
            self._handle_ses_reputation_ok(metrics=metrics,
                                           event_unix_ts=event_unix_ts)

        return self._get_pending_notifications()

    def _set_logger(self, logger):
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(self.__module__)
            self._logger.addHandler(logging.NullHandler())

    def _get_pending_notifications(self):
        return {
            'slack': self.slack_service.messages,
            'pager_duty': self.pager_duty_service.events
        }

    def _get_notification_responses(self):
        return {
            'slack': self.slack_service.responses,
            'pager_duty': self.pager_duty_service.responses
        }

    def _handle_ses_sending_quota_critical(self,
                                           utilization_percent,
                                           critical_percent,
                                           volume,
                                           max_volume,
                                           metric_iso_ts,
                                           event_iso_ts=None,
                                           event_unix_ts=None):
        self.logger.debug('SES sending quota is in a CRITICAL state!')
        self._log_handle_ses_quota_request(utilization_percent, critical_percent, 'CRITICAL')

        if self.notify_config.notify_pager_duty_on_ses_sending_quota:
            self.logger.debug('Pager Duty alerting is ENABLED, queuing TRIGGER event...')
            self.pager_duty_service.enqueue_ses_account_sending_quota_trigger_event(volume=volume,
                                                                                    max_volume=max_volume,
                                                                                    utilization_percent=utilization_percent,
                                                                                    threshold_percent=critical_percent,
                                                                                    metric_ts=metric_iso_ts,
                                                                                    event_iso_ts=event_iso_ts)
        else:
            self.logger.debug('Pager Duty alerting is DISABLED, skipping...')

        if self.notify_config.notify_slack_on_ses_sending_quota:
            self.logger.debug('Slack notifications is ENABLED, queuing message...')

            self.slack_service.enqueue_ses_account_sending_quota_message(threshold_name=THRESHOLD_CRITICAL,
                                                                         utilization_percent=utilization_percent,
                                                                         threshold_percent=critical_percent,
                                                                         volume=volume,
                                                                         max_volume=max_volume,
                                                                         metric_iso_ts=metric_iso_ts,
                                                                         event_unix_ts=event_unix_ts)
        else:
            self.logger.debug('Slack notifications is DISABLED, skipping...')

        self._log_handle_ses_quota_response()

    def _handle_ses_sending_quota_warning(self,
                                          utilization_percent,
                                          warning_percent,
                                          volume,
                                          max_volume,
                                          metric_iso_ts,
                                          event_unix_ts=None):
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
                                                                         metric_iso_ts=metric_iso_ts,
                                                                         event_unix_ts=event_unix_ts)
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

    def _handle_ses_reputation_critical(self, metrics, event_iso_ts=None, event_unix_ts=None):
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
                                                                                 event_iso_ts=event_iso_ts,
                                                                                 event_unix_ts=event_unix_ts,
                                                                                 action=action)
        else:
            self.logger.debug('Pager Duty alerting is DISABLED, skipping...')

        if self.notify_config.notify_slack_on_ses_reputation:
            self.logger.debug('Slack notifications is ENABLED, queuing message...')

            self.slack_service.enqueue_ses_account_reputation_message(threshold_name=THRESHOLD_CRITICAL,
                                                                      metrics=danger_metrics,
                                                                      event_unix_ts=event_unix_ts,
                                                                      action=action)
        else:
            self.logger.debug('Slack notifications is DISABLED, skipping...')

        self._log_handle_ses_reputation_response()

    def _handle_ses_reputation_warning(self, metrics, event_unix_ts=None):
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
                                                                      event_unix_ts=event_unix_ts,
                                                                      action=action)
        else:
            self.logger.debug('Slack notifications is DISABLED, skipping...')

        self._log_handle_ses_reputation_response()

    def _handle_ses_reputation_ok(self, metrics, event_unix_ts=None):
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
                                                                              event_unix_ts=event_unix_ts,
                                                                              action=ACTION_ENABLE)
                else:
                    self.logger.debug('Slack notifications is DISABLED, skipping...')

        else:
            self.logger.debug('SES management strategy is %s, status is %s, skipping...', SES_STRATEGY_MANAGED, THRESHOLD_OK)

        self._log_handle_ses_reputation_response()

    def _handle_notification_responses(self):
        for eid, r in self.pager_duty_service.responses:
            if (r.status_code >= 400) and (r.status_code <= 500):
                self.logger.debug('PagerDuty notification FAILURE for event: %s, received: %s.', eid, r.status_code)
                raise NotificationFailure('Failed to post event to PagerDuty: {event}, status: {status}'.format(event=eid,
                                                                                                                status=r.status_code))
        for ch, r in self.slack_service.responses:
            if (r.status_code >= 400) and (r.status_code <= 500):
                self.logger.debug('Slack notification FAILURE for channel: %s, received: %s.', ch, r.status_code)
                raise NotificationFailure('Failed to post to Slack channel: {channel}, status: {status}.'.format(channel=ch,
                                                                                                                 status=r.status_code))

        self.logger.debug('Notifications were all sent successfully!')

    def _log_handle_ses_quota_request(self, utilization_percent, threshold_percent, status):
        self.logger.debug('SES account sending percentage is at %s, threshold is at %s, status is %s!',
                          utilization_percent,
                          threshold_percent,
                          status)

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name__,
                                    method_name='handle_ses_quota',
                                    details={
                                        'utilization_percent': utilization_percent,
                                        'threshold_percent': threshold_percent,
                                        'status': status
                                    }))

    def _log_handle_ses_quota_response(self):
        self.logger.debug('SES account sending handler complete.')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='handle_ses_quota'))

    def _log_handle_ses_reputation_request(self, metrics, status):
        critical_count = len(metrics.critical)
        warning_count = len(metrics.warning)
        ok_count = len(metrics.ok)

        self.logger.debug('SES account reputation metrics - critical: %s, warning: %s, ok: %s, status is %s!',
                          critical_count,
                          warning_count,
                          ok_count,
                          status)

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name__,
                                    method_name='handle_ses_reputation',
                                    details=metrics))

    def _log_handle_ses_reputation_response(self):
        self.logger.debug('SES account reputation handler complete.')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='handle_ses_reputation'))
