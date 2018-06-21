# -*- coding: utf-8 -*-

'''
ses_account_monitor.services.pager_duty_service
~~~~~~~~~~~~~~~~

PagerDuty service module.
'''

from __future__ import division

from collections import deque

from ses_account_monitor.clients.http_client import HttpClient

from ses_account_monitor.config import (
    ACTION_ALERT,
    ACTION_DISABLE,
    PAGER_DUTY_SERVICE_CONFIG)

from ses_account_monitor.util import (
    iso8601_timestamp,
    unix_timestamp)

MAX_PAYLOAD_SIZE = (512 << 10)

SES_ACCOUNT_SENDING_QUOTA_CLASS_TYPE = 'ses_account_sending_quota'
SES_ACCOUNT_REPUTATION_CLASS_TYPE = 'ses_account_reputation'


class PagerDutyService(HttpClient):
    '''
    PagerDuty service class, inherits HttpClient.
    '''

    def __init__(self,
                 url=None,
                 routing_key=None,
                 config=None,
                 dry_run=False,
                 logger=None):
        '''
        Args:
            url (str): The PagerDuty service url.
            routing_key (str): The PagerDuty routing key.
            config (:obj:`PagerDutyServiceConfig`, optional): PagerDuty service configuration object.
            dry_run (:obj:`bool`, optional): Disable making live API calls. Defaults to False (make live API calls).
            logger (:obj:`logging.Logger`, optional): Logger instance. Defaults to None, which will create a logger instance.
        '''

        self._config = (config or PAGER_DUTY_SERVICE_CONFIG)
        self._dry_run = dry_run

        if routing_key is None:
            routing_key = self._config.routing_key

        if url is None:
            url = self._config.events_url

        self._routing_key = routing_key

        super(PagerDutyService, self).__init__(url=url,
                                               logger=logger)

        self.events = deque([])
        self.responses = []

    @property
    def config(self):
        '''
        obj (PagerDutyServiceConfig): PagerDuty service configuration object.
        '''

        return self._config

    @property
    def dry_run(self):
        '''
        bool: Flag to disable making live API calls.
        '''

        return self._dry_run

    def send_notifications(self, dry_run=False):
        '''
        Send all events in the queue to PagerDuty.

        Args:
            dry_run (:obj:`bool`, optional): Disable making live API calls. Defaults to False (make live API calls).

        Returns:
            tuple:
                send_status (bool): Returns True when notifications were actually sent, if False a dry run was executed.
                responses (:obj:`list` of :obj:`tuple`):
                    event_id (str): A identifier made up of the PagerDuty event_key and event_action.
                    responses (:obj:`list` of :obj:`requests.Response/dict`): List of response objects.
                        If a dry run occurred, will return dict objects containing the params for the request.
        '''

        self.logger.debug('Sending events to PagerDuty...')

        self.responses = []
        send_status = (not dry_run)

        if dry_run or self.dry_run:
            self.logger.debug('PagerDuty DRY RUN enabled, not sending %s notifications!', len(self.events))

            while self.events:
                event = self.events.popleft()
                event_key = event.get('dedup_key')
                event_action = event.get('event_action', '')
                event_id = 'debug::{action}::{name}'.format(name=event_key, action=event_action)

                self.logger.debug('Sending PagerDuty %s event...', event_id)
                self.responses.append((event_id, event))
        else:
            self.logger.debug('PagerDuty event count: %s', len(self.events))

            while self.events:
                event = self.events.popleft()
                event_key = event.get('dedup_key')
                event_action = event.get('event_action', '')
                event_id = '{action}::{name}'.format(name=event_key, action=event_action)

                self.logger.debug('Sending PagerDuty %s event...', event_id)

                response = self.post_json(payload=event)
                self.responses.append((event_id, response))

        return (send_status, self.responses)

    def enqueue_ses_account_sending_quota_trigger_event(self, *args, **kwargs):
        '''
        Adds a SES account sending quota trigger event to the event queue.

        This event is a TRIGGER and it should be sent when the emails sent in a 24 hour exceed the 24 hour limit.

        Args:
            volume (int): The number of SES emails sent for the 24 hour period.
            max_volume (int): The max number of SES emails allowed for the 24 hour period.
            utiliziation_percent (float): The percent of the quota used. Ex: 80% is represented as 80.
            threshold_percent (float): The threshold percent. Ex: 80% is represented as 80.
            event_iso_ts (:obj:`str`, optional): ISO 8601 timestamp.
                Default is None, which will cause the current time to be used.
            metric_ts (:obj:`str/int/datetime.datetime`, optional): The metric timestamp in any format.
                Default is None, which will cause the current time to be used.

        Returns:
            self (PagerDutyService): PagerDutyService instance.
        '''

        event = self.build_ses_account_sending_quota_trigger_event_payload(*args, **kwargs)
        self._enqueue_event(event)
        return self

    def enqueue_ses_account_sending_quota_resolve_event(self, *args, **kwargs):
        '''
        Adds a SES account sending quota resolve event to the event queue.

        This event is a RESOLVE, should be sent when emails sent in a 24 hour period are within the quota.

        Returns:
            self (PagerDutyService): PagerDutyService instance.
        '''

        event = self.build_ses_account_sending_quota_resolve_event_payload(*args, **kwargs)
        self._enqueue_event(event)
        return self

    def enqueue_ses_account_reputation_trigger_event(self, *args, **kwargs):
        '''
        Adds a SES account sending reputation trigger event to the event queue.

        This event is a TRIGGER and it should be sent when the account reputation exceeds thresholds.

        Args:
            metrics (:obj:`list` of :obj:`tuple`): List of tuples containing the metrics.
            event_iso_ts (:obj:`str`, optional): ISO 8601 timestamp of when the event occurred.
                Default is None, which will cause the current time to be used.
            event_unix_ts (:obj:`str`, optional): UNIX timestamp of when the event occurred.
                Default is None, which will cause the current time to be used.
            action (:obj:`str`, optional): The action taken in response to the event. Ex: alert, disable, enable.
                Default is None.

        Returns:
            self (PagerDutyService): PagerDutyService instance.
        '''

        event = self.build_ses_account_reputation_trigger_event_payload(*args, **kwargs)
        self._enqueue_event(event)
        return self

    def enqueue_ses_account_reputation_resolve_event(self, *args, **kwargs):
        '''
        Adds a SES account sending reputation resolve event to the event queue.

        This event is a RESOLVE, should be sent when reputation metrics are below thresholds.

        Returns:
            self (PagerDutyService): PagerDutyService instance.
        '''

        event = self.build_ses_account_reputation_resolve_event_payload(*args, **kwargs)
        self._enqueue_event(event)
        return self

    def build_ses_account_sending_quota_trigger_event_payload(self,
                                                              volume,
                                                              max_volume,
                                                              utilization_percent,
                                                              threshold_percent,
                                                              event_iso_ts=None,
                                                              metric_ts=None):
        '''
        Generates a TRIGGER event payload, when the SES account sending quota surpasses set thresholds.

        Args:
            volume (int): The number of SES emails sent for the 24 hour period.
            max_volume (int): The max number of SES emails allowed for the 24 hour period.
            utiliziation_percent (float): The percent of the quota used. Ex: 80% is represented as 80.
            threshold_percent (float): The threshold percent. Ex: 80% is represented as 80.
            event_iso_ts (:obj:`str`, optional): ISO 8601 timestamp.
                Default is None, which will cause the current time to be used.
            metric_ts (:obj:`str/int/datetime.datetime`, optional): The metric timestamp in any format.
                Default is None, which will cause the current time to be used.

        Returns:
            dict: The PagerDuty trigger event payload for SES account sending.
                payload (dict):
                    summary (str): Event summary.
                    timestamp (str): Event timestamp.
                    source (str): Event source.
                    severity (str): Event severity.
                    component (str): Event component.
                    group (str): Event group.
                    class (str): Event class.
                    custom_details (dict): Event custom details.
                routing_key (str): PagerDuty routing key.
                dedup_key (str): PagerDuty dedup key.
                event_action (str): Event action.
                client (str): Client name.
                client_url (str): Client url.
        '''

        return self._build_trigger_payload(summary='SES account sending quota is at capacity.',
                                           severity='critical',
                                           class_type=SES_ACCOUNT_SENDING_QUOTA_CLASS_TYPE,
                                           event_action='trigger',
                                           timestamp=event_iso_ts,
                                           custom_details=self._build_ses_account_quota_custom_details(volume=volume,
                                                                                                       max_volume=max_volume,
                                                                                                       utilization=utilization_percent,
                                                                                                       threshold=threshold_percent,
                                                                                                       ts=metric_ts),
                                           client='AWS Console',
                                           client_url=self.config.ses_console_url)

    def build_ses_account_reputation_trigger_event_payload(self,
                                                           metrics,
                                                           event_iso_ts=None,
                                                           event_unix_ts=None,
                                                           action=None):
        '''
        Generates a TRIGGER event payload, when the SES account reputation quota surpasses set thresholds.

        Args:
            metrics (:obj:`list` of :obj:`tuple`): List of tuples containing the metrics.
            event_iso_ts (:obj:`str`, optional): ISO 8601 timestamp of when the event occurred.
                Default is None, which will cause the current time to be used.
        event_unix_ts (:obj:`int/str`, optional): UNIX timestamp of when the event occurred.
                Default is None, which will cause the current time to be used.
            action (:obj:`str`, optional): The action taken in response to the event. Ex: alert, disable, enable.
                Default is None.

        Returns:
            dict: The PagerDuty trigger event payload for SES account reputation.
                payload (dict):
                    summary (str): Event summary.
                    timestamp (str): Event timestamp.
                    source (str): Event source.
                    severity (str): Event severity.
                    component (str): Event component.
                    group (str): Event group.
                    class (str): Event class.
                    custom_details (dict): Event custom details.
                routing_key (str): PagerDuty routing key.
                dedup_key (str): PagerDuty dedup key.
                event_action (str): Event action.
                client (str): Client name.
                client_url (str): Client url.
        '''

        return self._build_trigger_payload(summary='SES account reputation is at dangerous levels.',
                                           severity='critical',
                                           class_type=SES_ACCOUNT_REPUTATION_CLASS_TYPE,
                                           event_action='trigger',
                                           timestamp=event_iso_ts,
                                           custom_details=self._build_ses_reputation_custom_details(metrics=metrics,
                                                                                                    action=action,
                                                                                                    ts=event_unix_ts),
                                           client='AWS Console',
                                           client_url=self.config.ses_console_url)

    def build_ses_account_sending_quota_resolve_event_payload(self):
        '''
        Generates a RESOLVE event payload, when the SES account sending amount is within the quota.

        Returns:
            dict: The PagerDuty resolve event payload for SES account sending.
                routing_key (str): PagerDuty routing key.
                dedup_key (str): PagerDuty dedup key.
                event_action (str): PagerDuty event action.
        '''

        return self._build_resolve_payload(SES_ACCOUNT_SENDING_QUOTA_CLASS_TYPE)

    def build_ses_account_reputation_resolve_event_payload(self):
        '''
        Generates a RESOLVE event payload, when the SES account reputation is below thresholds.

        Returns:
            dict: The PagerDuty resolve event payload for SES account reputation.
                routing_key (str): PagerDuty routing key.
                dedup_key (str): PagerDuty dedup key.
                event_action (str): PagerDuty event action.
        '''

        return self._build_resolve_payload(SES_ACCOUNT_REPUTATION_CLASS_TYPE)

    def _build_trigger_payload(self,
                               summary,
                               severity,
                               class_type,
                               event_action,
                               custom_details=None,
                               timestamp=None,
                               client=None,
                               client_url=None):
        '''
        Generates a TRIGGER event payload.

        Args:
            summary (str): Event summary.
            severity (str): Event severity.
            class_type (str): Event class.
            event_action (str): Event action.
            custom_details (:obj:`obj`, optional): Event custom details.
            timestamp (:obj:`str`, optional): Event timestamp.
            client (:obj:`str`, optional): Client name.
            client_url (:obj:`str`, optional): Client url.

        Returns:
            dict: The PagerDuty trigger event payload.
                payload (dict):
                    summary (str): Event summary.
                    timestamp (str): Event timestamp.
                    source (str): Event source.
                    severity (str): Event severity.
                    component (str): Event component.
                    group (str): Event group.
                    class (str): Event class.
                    custom_details (obj): Event custom details.
                routing_key (str): PagerDuty routing key.
                dedup_key (str): PagerDuty dedup key.
                event_action (str): Event action.
                client (str): Client name.
                client_url (str): Client url.
        '''

        return {
            'payload': {
                'summary': summary,
                'timestamp': (timestamp or iso8601_timestamp()),
                'source': self.config.service_name,
                'severity': severity,
                'component': 'ses',
                'group': self._get_group(),
                'class': class_type,
                'custom_details': custom_details
            },
            'routing_key': self._routing_key,
            'dedup_key': self._get_dedupe_string(class_type),
            'event_action': event_action,
            'client': client,
            'client_url': client_url
        }

    def _build_resolve_payload(self, class_type):
        '''
        Generates a RESOLVE event payload.

        Args:
            class_type (str): PagerDuty event class.

        Returns:
            dict: The PagerDuty resolve event payload.
                routing_key (str): PagerDuty routing key.
                dedup_key (str): PagerDuty dedup key.
                event_action (str): PagerDuty event action.
        '''

        return {
            'routing_key': self._routing_key,
            'dedup_key': self._get_dedupe_string(class_type),
            'event_action': 'resolve'
        }

    def _build_ses_account_quota_custom_details(self, volume, max_volume, utilization, threshold, ts=None):
        '''
        Generate custom details for the SES account quota event payload.

        Args:
            volume (int): The number of SES emails sent for the 24 hour period.
            max_volume (int): The max number of SES emails allowed for the 24 hour period.
            utiliziation (float): The percent of the quota used. Ex: 80% is represented as 80.
            threshold (float): The threshold percent. Ex: 80% is represented as 80.
            ts (:obj:`str/int/datetime.datetime`, optional): The metric timestamp in any format.
                Default is None, which will cause the current time to be used.

        Returns:
            dict: SES account quota custom details object to be sent with the PagerDuty trigger event payload.
                aws_account_name (str): AWS account name.
                aws_region (str): AWS region.
                aws_environment (str): AWS environment.
                volume (int): The number of SES emails sent for the 24 hour period.
                max_volume (int): The max number of SES emails allowed for the 24 hour period.
                utilization (str): The percent of the quota used.
                threshold (str): The threshold percent.
                ts (str): Metric timestamp.
                version (str): Custom details version.
        '''

        return {
            'aws_account_name': self.config.aws_account_name,
            'aws_region': self.config.aws_region,
            'aws_environment': self.config.aws_environment,
            'volume': volume,
            'max_volume': max_volume,
            'utilization': '{:.0%}'.format(utilization / 100),
            'threshold': '{:.0%}'.format(threshold / 100),
            'ts': str((ts or unix_timestamp())),
            'version': 'v1.2018.06.18'
        }

    def _build_ses_reputation_custom_details(self, metrics, action=None, ts=None):
        '''
        Generate custom details for the SES account reputation event payload.

        Args:
            metrics (:obj:`list` of :obj:`tuple`): List of tuples containing the metrics.
            action (:obj:`str`, optional): The action taken in response to the event. Ex: alert, disable, enable.
                Default is None.
            ts (:obj:`str/int/datetime.datetime`, optional): The metric timestamp in any format.
                Default is None, which will cause the current time to be used.

        Returns:
            dict: SES account reputation custom details object to be sent with the PagerDuty trigger event payload.
                aws_account_name (str): AWS account name.
                aws_region (str): AWS region.
                aws_environment (str): AWS environment.
                ts (str): Metric timestamp.
                version (str): Custom details version.
                action (str): Action taken.
                bounce_rate (str): Bounce rate, formatted as a percentage.
                bounce_rate_threshold (str): Bounce rate threshold, formatted as a percentage.
                bounce_rate_timestamp (str): Bounce rate timestamp.
                complaint_rate (str): Complaint rate, formatted as a percentage.
                complaint_rate_threshold (str): Complaint rate threshold, formatted as a percentage.
                complaint_rate_timestamp (str): Complaint rate timestamp.
        '''

        action = (action or ACTION_ALERT)

        details = {
            'aws_account_name': self.config.aws_account_name,
            'aws_region': self.config.aws_region,
            'aws_environment': self.config.aws_environment,
            'ts': str((ts or unix_timestamp())),
            'version': 'v1.2018.06.18',
            'action': action
        }

        if action == ACTION_DISABLE:
            details['action_message'] = 'SES account sending is disabled.'

        if action == ACTION_ALERT:
            details['action_message'] = 'SES account is in danger of being suspended.'

        for label, current_percent, threshold_percent, ts in metrics:
            name = label.replace(' ', '_').lower()
            details[name] = '{:.2%}'.format(current_percent / 100)
            details[name + '_threshold'] = '{:.2%}'.format(threshold_percent / 100)
            details[name + '_timestamp'] = str(ts)

        return details

    def _get_dedupe_string(self, target):
        '''
        Get the PagerDuty dedupe string, this helps reduce duplicate events.

        Args:
            target (str): The name of the target to get the dedupe string for. Typically the event class (class_type).

        Returns:
            str: Formatted as '$SERVICE/$TARGET'. Ex: 'supercoolco-us-west-2-lambda-ses-account-monitor/ses_account_reputation'.
        '''

        return '{service}/{target}'.format(service=self.config.service_name, target=target)

    def _get_group(self):
        '''
        Get the event group.

        Returns:
            str: Formatted as 'aws-$AWS_ACCOUNT_NAME'. Ex: 'aws-supercoolco'.
        '''

        return 'aws-{}'.format(self.config.aws_account_name)

    def _enqueue_event(self, event):
        '''
        Add a single event to the events queue.
        '''

        self.events.append(event)
