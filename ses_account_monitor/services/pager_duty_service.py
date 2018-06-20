# -*- coding: utf-8 -*-
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
    Send events to PagerDuty.
    '''

    def __init__(self,
                 url=None,
                 routing_key=None,
                 config=None,
                 dry_run=False,
                 logger=None):

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

    @property
    def config(self):
        return self._config

    @property
    def dry_run(self):
        return self._dry_run

    def send_notifications(self, dry_run=None):
        self.logger.debug('Sending events to PagerDuty...')

        responses = []
        send_status = (not dry_run)

        if dry_run or self.dry_run:
            self.logger.debug('PagerDuty DRY RUN enabled, not sending %s notifications!', len(self.events))
            responses.extend(self.events)
            self.events.clear()
            return responses

        self.logger.debug('PagerDuty event count: %s', len(self.events))

        while self.events:
            event = self.events.popleft()

            self.logger.debug('Sending PagerDuty %s event...', event.get('payload', {}).get('class', ''))

            response = self.post_json(payload=event)
            responses.append(response)

        return (send_status, responses)

    def enqueue_ses_account_sending_quota_trigger_event(self, *args, **kwargs):
        event = self.build_ses_account_sending_quota_trigger_event_payload(*args, **kwargs)
        self._enqueue_event(event)
        return self

    def enqueue_ses_account_sending_quota_resolve_event(self, *args, **kwargs):
        event = self.build_ses_account_sending_quota_resolve_event_payload(*args, **kwargs)
        self._enqueue_event(event)
        return self

    def enqueue_ses_account_reputation_trigger_event(self, *args, **kwargs):
        event = self.build_ses_account_reputation_trigger_event_payload(*args, **kwargs)
        self._enqueue_event(event)
        return self

    def enqueue_ses_account_reputation_resolve_event(self, *args, **kwargs):
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
                                                           metric_ts=None,
                                                           action=None):
        return self._build_trigger_payload(summary='SES account reputation is at dangerous levels.',
                                           severity='critical',
                                           class_type=SES_ACCOUNT_REPUTATION_CLASS_TYPE,
                                           event_action='trigger',
                                           timestamp=event_iso_ts,
                                           custom_details=self._build_ses_reputation_custom_details(metrics=metrics,
                                                                                                    action=action,
                                                                                                    ts=metric_ts),
                                           client='AWS Console',
                                           client_url=self.config.ses_console_url)

    def build_ses_account_sending_quota_resolve_event_payload(self):
        return self._build_resolve_payload(SES_ACCOUNT_SENDING_QUOTA_CLASS_TYPE)

    def build_ses_account_reputation_resolve_event_payload(self):
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
        return {
            'routing_key': self._routing_key,
            'dedup_key': self._get_dedupe_string(class_type),
            'event_action': 'resolve'
        }

    def _build_ses_account_quota_custom_details(self, volume, max_volume, utilization, threshold, ts=None):
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
            details[name] = '{:.2%}'.format(current_percent)
            details[name + '_threshold'] = '{:.2%}'.format(threshold_percent)
            details[name + '_timestamp'] = str(ts)

        return details

    def _get_dedupe_string(self, target):
        return '{service}/{target}'.format(service=self.config.service_name, target=target)

    def _get_group(self):
        return 'aws-{}'.format(self.config.aws_account_name)

    def _enqueue_events(self, events):
        self.events.extend(events)

    def _enqueue_event(self, event):
        self.events.append(event)
