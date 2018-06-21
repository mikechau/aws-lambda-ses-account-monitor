# -*- coding: utf-8 -*-

'''
ses_account_monitor.monitor
~~~~~~~~~~~~~~~~

SES account monitor monitor module.
'''

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
    SES_MONITOR_STRATEGY,
    SES_MONITOR_STRATEGY_ALERT,
    SES_MONITOR_STRATEGY_MANAGED,
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
    '''
    Custom exception for notification failures, inherits Exception.
    '''
    pass


class Monitor(object):
    '''
    Monitor classs, retrieves SES metric data and if past set thresholds will send alerts to connected notification services.
    '''

    def __init__(self,
                 ses_management_strategy=None,
                 notify_config=False,
                 thresholds=None,
                 cloudwatch_client=None,
                 cloudwatch_service=None,
                 ses_client=None,
                 ses_service=None,
                 slack_service=None,
                 pager_duty_service=None,
                 monitor_ses_reputation=MONITOR_SES_REPUTATION,
                 monitor_ses_sending_quota=MONITOR_SES_SENDING_QUOTA,
                 logger=None):
        '''
        Args:
            ses_management_strategy (:obj:`str`, optional): SES management strategy, whether to alert only or managed SES (autopause).
                Default is None, which will use alert. Ex: managed, alert.
            notify_config (:obj:`NotifyConfig`, optional): The notification configuration.
                Default is None, which will use the configuration specified in the config module.
            thresholds (:obj:`dict`, optional): The threshold configuration.
                Default is None, which will use the configuration specified in the config module.
            cloudwatch_client (:obj:`botocore.client.CloudWatch`, optional): CloudWatch client.
                Specify this to pass it to the cloudwatch_service and cloudwatch_service must not be set.
            cloudwatch_service (:obj:`CloudWatchService`, optional): CloudWatch service instance.
                Default is None, which will create instance using configuration settings from the config module.
            ses_client (:obj:`botocore.client.SES`, optional): SES client.
                Specify this to pass it to the ses_service and ses_service must not be set.
            ses_service (:obj:`SesService`, optional): SES service instance.
                Default is None, which will create instance using configuration settings from the config module.
            slack_service (:obj:`SlackService`, optional): Slack service instance.
                Default is None, which will create instance using configuration settings from the config module.
            pager_duty_service (:obj:`PagerDutyService`, optional): PagerDuty service instance.
            monitor_ses_reputation (:obj:`bool`, optional): Flag for enabling SES account reputation monitoring.
            monitor_ses_sending_quota (:obj:`bool`, optional): Flag for enabling SES account sending quota monitoring.
            logger (:obj:`logging.Logger`, optional): Logger instance. Defaults to None, which will create a logger instance.
        '''

        self._notify_config = (notify_config or NOTIFY_CONFIG)
        self._thresholds = (thresholds or THRESHOLDS)
        self._logger = (logger or self._build_logger())

        self.monitor_ses_reputation = monitor_ses_reputation
        self.monitor_ses_sending_quota = monitor_ses_sending_quota
        self.ses_management_strategy = (ses_management_strategy or SES_MONITOR_STRATEGY)
        self.ses_service = (ses_service or SesService(client=ses_client))
        self.cloudwatch_service = (cloudwatch_service or CloudWatchService(client=cloudwatch_client))
        self.pager_duty_service = (pager_duty_service or PagerDutyService())
        self.slack_service = (slack_service or SlackService())

    @property
    def ses_sending_quota_warning_percent(self):
        '''
        float: SES sending quota WARNING percentage.
        '''
        return self._thresholds['ses_sending_quota_warning_percent']

    @property
    def ses_sending_quota_critical_percent(self):
        '''
        float: SES sending quota CRITICAL percentage.
        '''
        return self._thresholds['ses_sending_quota_critical_percent']

    @property
    def logger(self):
        '''
        obj (logger.Logger): The logger instance.
        '''
        return self._logger

    @property
    def notify_config(self):
        '''
        obj (NotifyConfig): The notify config instance.
        '''
        return self._notify_config

    def send_notifications(self, raise_on_errors=False):
        '''
        Send all notifications.

        Args:
            raise_on_errors (:obj:`bool`, optional): Flag to raise exceptions on notification failures.
                A NotificationFailure exception is raised when notification HTTP responses return status codes in the 4XX-5XX range.
                Default is set to False.

        Returns:
            dict: Object containing the notification responses from PagerDuty and Slack.
                pager_duty (:obj:`list` of :obj:`tuple`): List of tuples containing the event id and response.
                    event_id (str): PagerDuty event id.
                    response (requests.Response/dict): Response object. If a dry run was executed will be a dict of the request params.
                slack (:obj:`list` of :obj:`tuple`): List of tuples containing the channel and response.
                    channel (str): Slack channel.
                    response (requests.Response/dict): Response object. If a dry run was executed will be a dict of the request params.
        '''

        self.logger.debug('Sending notifications...')
        self.pager_duty_service.send_notifications()
        self.slack_service.send_notifications()
        self.logger.debug('Finished sending all notifications!')

        if raise_on_errors:
            self._handle_notification_responses()

        return self._get_notification_responses()

    def handle_ses_sending_quota(self, target_datetime=None):
        '''
        Reviews the SES sending quota and enqueues notifications if thresholds have been exceeded.

        Args:
            target_datetime (datetime.datetime): Datetime object. Default is None, if not set will use the current datetime.

        Returns:
            dict: Queued notifications for PagerDuty and Slack.
                pager_duty (collections.deque): Pager Duty events queue.
                slack (collections.deque): Slack messages queue.

            A empty dict will be returned if SES account sending quota monitoring is disabled or if the strategy is not a valid one.
        '''

        if not self.monitor_ses_sending_quota:
            self.logger.debug('Handling SES account sending quota is DISABLED, skipping...')
            return {}

        self.logger.debug('Handling SES account sending quota...')

        if (self.ses_management_strategy != SES_MONITOR_STRATEGY_MANAGED) and (self.ses_management_strategy != SES_MONITOR_STRATEGY_ALERT):
            self.logger.debug('SES management strategy %s is not VALID, skipping!', self.ses_management_strategy)
            return {}

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

    def handle_ses_reputation(self, target_datetime=None, period=None, metric_timedelta=None):
        '''
        Reviews the SES account reputation and enqueues notifications if thresholds have been exceeded.

        Args:
            target_datetime (datetime.datetime): Datetime object. Default is None, if not set will use the current datetime.

        Returns:
            dict: Queued notifications for PagerDuty and Slack.
                pager_duty (collections.deque): Pager Duty events queue.
                slack (collections.deque): Slack messages queue.

            A empty dict will be returned if SES account sending quota monitoring is disabled or if the strategy is not a valid one.
        '''

        self.logger.debug('Handling SES account reputation...')

        if not self.monitor_ses_reputation:
            self.logger.debug('SES reputation is DISABLED, skipping...')
            return {}

        if (self.ses_management_strategy != SES_MONITOR_STRATEGY_MANAGED) and (self.ses_management_strategy != SES_MONITOR_STRATEGY_ALERT):
            self.logger.debug('SES management strategy %s is not VALID, skipping!', self.ses_management_strategy)
            return {}

        target_datetime = (target_datetime or current_datetime())
        event_iso_ts = iso8601_timestamp(target_datetime)
        event_unix_ts = unix_timestamp(target_datetime)

        metrics = self.cloudwatch_service.get_ses_account_reputation_metrics(target_datetime=target_datetime,
                                                                             period=period,
                                                                             metric_timedelta=metric_timedelta)

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

    def _build_logger(self):
        '''
        Builds a logger instance.

        Returns:
            obj (logging.Logger): The Logger instance.
        '''

        logger = logging.getLogger(self.__module__)
        logger.addHandler(logging.NullHandler())
        return logger

    def _get_pending_notifications(self):
        '''
        Gets the notification queues for PagerDuty and Slack.

        Returns:
            dict: Queued notifications for PagerDuty and Slack.
                pager_duty (collections.deque): Pager Duty events queue.
                slack (collections.deque): Slack messages queue.
        '''

        return {
            'slack': self.slack_service.messages,
            'pager_duty': self.pager_duty_service.events
        }

    def _get_notification_responses(self):
        '''
        Gets the notification queues for PagerDuty and Slack.

        Returns:
            dict: Object containing the notification responses from PagerDuty and Slack.
                pager_duty (:obj:`list` of :obj:`tuple`): List of tuples containing the event id and response.
                    event_id (str): PagerDuty event id.
                    response (requests.Response/dict): Response object. If a dry run was executed will be a dict of the request params.
                slack (:obj:`list` of :obj:`tuple`): List of tuples containing the channel and response.
                    channel (str): Slack channel.
                    response (requests.Response/dict): Response object. If a dry run was executed will be a dict of the request params.
        '''

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
        '''
        Actions taken when SES sending quota is in a CRITICAL state.

        Args:
            utilization_percent (float/int): Utilization percentage. 80% is 80.
            critical_percent (float/int): Critical threshold percentage. 80% is 80.
            volume (float/int): Number of emails sent.
            max_volume (float/int): Max number of emails allowed to be sent.
            metric_iso_ts (str): ISO 8601 timestamp.
            event_iso_ts (:obj:`str`, optional): ISO 8601 timestamp.
                Default is None, if not set will use current time.
            event_unix_ts (:obj:`str/int`, optional): UNIX timestamp.
                Default is None, if not set will use current time.
        '''

        self.logger.debug('SES sending quota is in a CRITICAL state!')
        self._log_handle_ses_quota_request(utilization_percent, critical_percent, 'CRITICAL')

        if self.notify_config.notify_pager_duty_on_ses_sending_quota:
            self.logger.debug('PagerDuty alerting is ENABLED, queuing TRIGGER event...')
            self.pager_duty_service.enqueue_ses_account_sending_quota_trigger_event(volume=volume,
                                                                                    max_volume=max_volume,
                                                                                    utilization_percent=utilization_percent,
                                                                                    threshold_percent=critical_percent,
                                                                                    metric_ts=metric_iso_ts,
                                                                                    event_iso_ts=event_iso_ts)
        else:
            self.logger.debug('PagerDuty alerting is DISABLED, skipping...')

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
        '''
        Actions taken when SES sending quota is in a WARNING state.

        Args:
            utilization_percent (float/int): Utilization percentage. 80% is 80.
            warning_percent (float/int): Warning threshold percentage. 80% is 80.
            volume (float/int): Number of emails sent.
            max_volume (float/int): Max number of emails allowed to be sent.
            metric_iso_ts (str): ISO 8601 timestamp.
            event_unix_ts (:obj:`str/int`, optional): UNIX timestamp.
                Default is None, if not set will use current time.
            event_iso_ts (:obj:`str`, optional): ISO 8601 timestamp.
                Default is None, if not set will use current time.
        '''

        self.logger.debug('SES sending quota is in a WARNING state!')

        self._log_handle_ses_quota_request(utilization_percent, warning_percent, 'WARNING')

        if self.notify_config.notify_pager_duty_on_ses_sending_quota:
            self.logger.debug('PagerDuty alerting is ENABLED, queuing RESOLVE event...')
            self.pager_duty_service.enqueue_ses_account_sending_quota_resolve_event()
        else:
            self.logger.debug('PagerDuty alerting is DISABLED, skipping...')

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
        '''
        Actions taken when SES sending quota is in a OK state.

        Args:
            utilization_percent (float/int): Utilization percentage. 80% is 80.
            warning_percent (float/int): Warning threshold percentage. 80% is 80.
        '''

        self.logger.debug('SES sending quota is in a OK state!')

        self._log_handle_ses_quota_request(utilization_percent, warning_percent, 'OK')

        if self.notify_config.notify_pager_duty_on_ses_sending_quota:
            self.logger.debug('PagerDuty alerting is ENABLED, queuing RESOLVE event...')
            self.pager_duty_service.enqueue_ses_account_sending_quota_resolve_event()
        else:
            self.logger.debug('PagerDuty alerting is DISABLED, skipping...')

        self._log_handle_ses_quota_response()

    def _handle_ses_reputation_critical(self, metrics, event_iso_ts=None, event_unix_ts=None):
        '''
        Actions taken when SES account reputation is in a CRITICAL state.

        Args:
            metrics (:obj:`list` of :obj:`tuple`): List of tuples containing the metrics.
            event_unix_ts (:obj:`str`, optional): UNIX timestamp of when the event occurred.
                Default is None, which will cause the current time to be used.
            event_iso_ts (:obj:`str`, optional): ISO 8601 timestamp of when the event occurred.
                Default is None, which will cause the current time to be used.
        '''

        self.logger.debug('SES account reputation has metrics in a %s state!', THRESHOLD_CRITICAL)

        self._log_handle_ses_reputation_request(metrics=metrics,
                                                status=THRESHOLD_CRITICAL)

        danger_metrics = (metrics.critical + metrics.warning)
        action = ACTION_ALERT

        if self.ses_management_strategy == SES_MONITOR_STRATEGY_MANAGED:
            self.logger.debug('SES management strategy is %s, status is %s, DISABLING...', SES_MONITOR_STRATEGY_MANAGED, THRESHOLD_CRITICAL)
            self.ses_service.disable_account_sending()
            action = ACTION_DISABLE
        else:
            self.logger.debug('SES management strategy is %s, status is %s, skipping...', SES_MONITOR_STRATEGY_MANAGED, THRESHOLD_CRITICAL)

        if self.notify_config.notify_pager_duty_on_ses_reputation:
            self.logger.debug('PagerDuty alerting is ENABLED, queuing TRIGGER event...')
            self.pager_duty_service.enqueue_ses_account_reputation_trigger_event(metrics=danger_metrics,
                                                                                 event_iso_ts=event_iso_ts,
                                                                                 event_unix_ts=event_unix_ts,
                                                                                 action=action)
        else:
            self.logger.debug('PagerDuty alerting is DISABLED, skipping...')

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
        '''
        Actions taken when SES account reputation is in a WARNING state.

        Args:
            metrics (:obj:`list` of :obj:`tuple`): List of tuples containing the metrics.
            event_unix_ts (:obj:`str`, optional): UNIX timestamp of when the event occurred.
                Default is None, which will cause the current time to be used.
        '''

        action = ACTION_ALERT

        self.logger.debug('SES account reputation has metrics in a %s state!', THRESHOLD_WARNING)

        self._log_handle_ses_reputation_request(metrics=metrics,
                                                status=THRESHOLD_WARNING)

        if self.ses_management_strategy == SES_MONITOR_STRATEGY_MANAGED:
            self.logger.debug('SES management strategy is %s, status is %s, ENABLING...', SES_MONITOR_STRATEGY_MANAGED, THRESHOLD_WARNING)

            if not self.ses_service.is_account_sending_enabled():
                self.logger.debug('SES account sending is currently DISABLED! ENABLING...')
                self.ses_service.enable_account_sending()

                action = ACTION_ENABLE
        else:
            self.logger.debug('SES management strategy is %s, status is %s, skipping...', SES_MONITOR_STRATEGY_MANAGED, THRESHOLD_CRITICAL)

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
        '''
        Actions taken when SES account reputation is in a CRITICAL state.

        Args:
            metrics (:obj:`list` of :obj:`tuple`): List of tuples containing the metrics.
            event_unix_ts (:obj:`str`, optional): UNIX timestamp of when the event occurred.
                Default is None, which will cause the current time to be used.
        '''

        self.logger.debug('SES account reputation has metrics in a %s state!', THRESHOLD_OK)

        self._log_handle_ses_reputation_request(metrics=metrics,
                                                status=THRESHOLD_OK)

        if self.ses_management_strategy == SES_MONITOR_STRATEGY_MANAGED:
            self.logger.debug('SES management strategy is %s, status is %s, ENABLING...', SES_MONITOR_STRATEGY_MANAGED, THRESHOLD_OK)

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
            self.logger.debug('SES management strategy is %s, status is %s, skipping...', SES_MONITOR_STRATEGY_MANAGED, THRESHOLD_OK)

        self._log_handle_ses_reputation_response()

    def _handle_notification_responses(self):
        '''
        Review notification responses returned 4XX-5XX responses.

        Raises:
            NotificationFailure: When a notification HTTP response is within the 4XX-5XX range.
        '''

        if self.pager_duty_service.dry_run:
            self.logger.debug('PagerDuty service DRY RUN is ENABLED, skipping notification checks...')
        else:
            self.logger.debug('Reviewing PagerDuty notification responses...')

            for eid, r in self.pager_duty_service.responses:
                if (r.status_code >= 400) and (r.status_code <= 500):
                    self.logger.debug('PagerDuty notification FAILURE for event: %s, received: %s.', eid, r.status_code)
                    raise NotificationFailure('Failed to post event to PagerDuty: {event}, status: {status}'.format(event=eid,
                                                                                                                    status=r.status_code))

        if self.slack_service.dry_run:
            self.logger.debug('Slack service DRY RUN is ENABLED, skipping notification checks...')
        else:
            self.logger.debug('Reviewing Slack notification responses...')

            for ch, r in self.slack_service.responses:
                if (r.status_code >= 400) and (r.status_code <= 500):
                    self.logger.debug('Slack notification FAILURE for channel: %s, received: %s.', ch, r.status_code)
                    raise NotificationFailure('Failed to post to Slack channel: {channel}, status: {status}.'.format(channel=ch,
                                                                                                                     status=r.status_code))

        self.logger.debug('Notifications were all sent successfully!')

    def _log_handle_ses_quota_request(self, utilization_percent, threshold_percent, status):
        '''
        Log the SES account quota handler request.

        Args:
            utilization_percent (float/int): Utilization percentage. 80% is 80.
            threshold_percent (float/int): Threshold percentage. 80% is 80.
            status (str): The status of the SES account quota. Ex: CRITICAL, WARNING, OK.
        '''

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
        '''
        Log the SES account quota handler response.
        '''

        self.logger.debug('SES account sending handler complete.')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='handle_ses_quota'))

    def _log_handle_ses_reputation_request(self, metrics, status):
        '''
        Log the SES account reputation handler request.
        '''

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
        '''
        Log the SES account reputation handler response.
        '''

        self.logger.debug('SES account reputation handler complete.')

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='handle_ses_reputation'))
