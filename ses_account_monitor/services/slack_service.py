# -*- coding: utf-8 -*-
from __future__ import division

from collections import deque

from ses_account_monitor.clients.http_client import HttpClient

from ses_account_monitor.config import (
    ACTION_ALERT,
    ACTION_PAUSE,
    SLACK_SERVICE_CONFIG,
    THRESHOLD_CRITICAL,
    THRESHOLD_OK,
    THRESHOLD_WARNING)

from ses_account_monitor.util import (
    current_unix_timestamp)

THRESHOLD_COLOR = {
    THRESHOLD_CRITICAL: 'danger',
    THRESHOLD_OK: 'ok',
    THRESHOLD_WARNING: 'warning'
}


class SlackService(HttpClient):
    '''
    Send messages to Slack.
    '''

    def __init__(self,
                 url=None,
                 channels=None,
                 config=None,
                 dry_run=False,
                 logger=None):

        self._config = (config or SLACK_SERVICE_CONFIG)
        self._dry_run = dry_run

        if url is None:
            url = self._config.webhook_url

        super(SlackService, self).__init__(url=url,
                                           logger=logger)

        self.messages = deque([])
        self.channels = (channels or self._config.channels)

    @property
    def config(self):
        return self._config

    @property
    def dry_run(self):
        return self._dry_run

    def send_notifications(self, dry_run=None):
        self.logger.debug('Sending notifications to Slack channels...')

        responses = []
        send_status = (not dry_run)

        if dry_run or self.dry_run:
            self.logger.debug('Slack DRY RUN enabled, not sending notifications!')

            while self.messages:
                message = self.messages.popleft()

                channel_messages = self._build_message_with_channels(message)
                responses.extend(channel_messages)

            return responses

        while self.messages:
            message = self.messages.popleft()

            self.logger.debug('Slack channel count: %s', len(self.channels))

            for channel in self.channels:
                self.logger.debug('Sending Slack notification to %s...', channel)

                payload = {'channel': channel}
                payload.update(message)

                response = self.post_json(payload=message)
                responses.append(response)

        return (send_status, responses)

    def enqueue_ses_account_sending_quota_message(self, *args, **kwargs):
        message = self.build_ses_account_sending_quota_payload(*args, **kwargs)
        self._enqueue_message(message)
        return self

    def enqueue_ses_account_reputation_message(self, *args, **kwargs):
        message = self.build_ses_account_reputation_payload(*args, **kwargs)
        self._enqueue_message(message)
        return self

    def build_ses_account_sending_quota_payload(self,
                                                threshold_name,
                                                utilization_percent,
                                                threshold_percent,
                                                volume,
                                                max_volume,
                                                ts=None):

        payload = {
            'attachments': [{
                'fallback': 'SES account sending rate has breached {} threshold.'.format(threshold_name),
                'color': self._get_color(threshold_name),
                'fields': [
                    {
                        'title': 'Service',
                        'value': '<{}|SES Account Sending>'.format(self.config.ses_console_url),
                        'short': True
                    },
                    {
                        'title': 'Account',
                        'value': self.config.aws_account_name,
                        'short': True
                    },
                    {
                        'title': 'Region',
                        'value': self.config.aws_region,
                        'short': True
                    },
                    {
                        'title': 'Environment',
                        'value': self.config.aws_environment,
                        'short': True
                    },
                    {
                        'title': 'Status',
                        'value': threshold_name,
                        'short': True
                    },
                    {
                        'title': 'Threshold',
                        'value': '{:.2%}'.format(threshold_percent / 100),
                        'short': True
                    },
                    {
                        'title': 'Utilization',
                        'value': '{:.2%}'.format(utilization_percent / 100),
                        'short': True
                    },
                    {
                        'title': 'Volume / Max',
                        'value': '{sent} / {max}'.format(sent=volume, max=max_volume),
                        'short': True
                    },
                    {
                        'title': 'Message',
                        'value': 'SES account sending rate has breached the {} threshold.'.format(threshold_name),
                        'short': False
                    }
                ],
                'footer': self.config.service_name,
                'footer_icon': self.config.footer_icon_url,
                'ts': (ts or current_unix_timestamp())
            }],
            'icon_emoji': self.config.icon_emoji,
            'username': 'SES Account Monitor'
        }

        return payload

    def build_ses_account_reputation_payload(self,
                                             threshold_name,
                                             metrics,
                                             ts=None,
                                             action=None):

        fallback_text, primary_text = self._build_ses_reputation_text(threshold_name)

        message = {
            'attachments': [
                {
                    'fallback': fallback_text,
                    'color': self._get_color(threshold_name),
                    'fields': [
                        {
                            'title': 'Service',
                            'value': '<{}|SES Account Reputation>'.format(self.config.ses_reputation_dashboard_url),
                            'short': True
                        },
                        {
                            'title': 'Account',
                            'value': self.config.aws_account_name,
                            'short': True
                        },
                        {
                            'title': 'Region',
                            'value': self.config.aws_region,
                            'short': True
                        },
                        {
                            'title': 'Environment',
                            'value': self.config.aws_environment,
                            'short': True
                        },
                        {
                            'title': 'Status',
                            'value': threshold_name,
                            'short': True
                        },
                        {
                            'title': 'Action',
                            'value': (action or ACTION_ALERT).upper(),
                            'short': True
                        }
                    ],
                    'footer': self.config.service_name,
                    'footer_icon': self.config.footer_icon_url,
                    'ts': (ts or current_unix_timestamp())
                }
            ],
            'icon_emoji': self.config.icon_emoji,
            'username': 'SES Account Monitor'
        }

        for label, utilization_percent, threshold_percent, ts in metrics:
            metric_value = '{utilization:.2%} / {threshold:.2%}'.format(utilization=utilization_percent,
                                                                        threshold=threshold_percent)

            message['attachments'][0]['fields'].extend(
                [{'title': '{} / Threshold'.format(label),
                  'value': metric_value,
                  'short': True},
                 {'title': '{} Time'.format(label),
                  'value': str(ts),
                  'short': True}])

        message['attachments'][0]['fields'].append({
            'title': 'Message',
            'value': primary_text,
            'short': False
        })

        return message

    def _get_color(self, threshold_name):
        return THRESHOLD_COLOR.get(threshold_name.upper(), '')

    def _build_ses_reputation_text(self, threshold_name):
        threshold_name = threshold_name.upper()

        if (threshold_name == THRESHOLD_CRITICAL) or (threshold_name == THRESHOLD_WARNING):
            fallback_text = 'SES account reputation has breached {} threshold.'.format(threshold_name)
            primary_text = 'SES account reputation has breached the {} threshold.'.format(threshold_name)
        elif threshold_name == THRESHOLD_OK:
            fallback_text = 'SES account reputation has recovered.'
            primary_text = 'SES account reputation status is {}.'.format(threshold_name)

        return (fallback_text, primary_text)

    def _build_message_with_channels(self, base_payload):
        messages = []
        for channel in self.channels:
            payload = {'channel': channel}
            payload.update(base_payload)
            messages.append(payload)

        return messages

    def _enqueue_messages(self, messages):
        self.messages.extend(messages)

    def _enqueue_message(self, message):
        self.messages.append(message)
