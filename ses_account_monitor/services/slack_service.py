# -*- coding: utf-8 -*-
from collections import deque

from ses_account_monitor.clients.http_client import HttpClient

from ses_account_monitor.config import (
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
                 url,
                 config=None,
                 dry_run=False,
                 logger=None):
        super(SlackService, self).__init__(url=url,
                                           logger=logger)
        self._config = (config or SLACK_SERVICE_CONFIG)
        self._dry_run = dry_run

        self.messages = deque([])

    @property
    def config(self):
        return self._config

    @property
    def dry_run(self):
        return self._dry_run

    def send_notifications(self, dry_run=None):
        responses = []
        send_status = (not dry_run)

        if dry_run or self.dry_run:
            while self.messages:
                message = self.messages.popleft()
                responses.append(responses)

            return responses

        while self.messages:
            message = self.messages.popleft()
            response = self.post_json(payload=message)
            responses.append(response)

        return (send_status, responses)

    def build_ses_account_sending_quota_message(self,
                                                threshold_name,
                                                current_percent,
                                                threshold_percent,
                                                sent_emails,
                                                max_emails,
                                                ts=None,
                                                enqueue=False):
        payload = {
            'attachments': [
                {
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
                            'value': '{:.2%}'.format(threshold_percent),
                            'short': True
                        },
                        {
                            'title': 'Current',
                            'value': '{:.2%}'.format(current_percent),
                            'short': True
                        },
                        {
                            'title': 'Sent / Max',
                            'value': '{sent} / {max}'.format(sent=sent_emails, max=max_emails),
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
                }
            ],
            'username': 'SES Account Monitor'
        }

        if enqueue:
            self._enqueue_message(payload)

        return payload

    def build_ses_account_reputation_message(self,
                                             threshold_name,
                                             metrics,
                                             ts=None,
                                             enqueue=False):

        fallback_message, message = self._build_ses_reputation_messages(threshold_name)

        metric_names = ', '.join(map(lambda x: x[0], metrics))

        payload = {
            'attachments': [
                {
                    'fallback': fallback_message,
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
                        }
                    ],
                    'footer': self.config.service_name,
                    'footer_icon': self.config.footer_icon_url,
                    'ts': (ts or current_unix_timestamp())
                }
            ],
            'username': 'SES Account Monitor'
        }

        payload['attachments'].append({
            'title': 'Metrics',
            'value': metric_names
        })

        for label, current_percent, threshold_percent, ts in metrics:
            metric_value = '{current:.2%} / {threshold:.2%}'.format(current=current_percent,
                                                                    threshold=threshold_percent)

            payload['attachments'].extend(
                [{'title': '{} / Threshold'.format(label),
                  'value': metric_value,
                  'short': True},
                 {'title': '{} Time'.format(label),
                  'value': str(ts),
                  'short': True}])

        payload['attachments'].append({
            'title': 'Message',
            'value': message,
            'short': False
        })

        if enqueue:
            self._enqueue_message(payload)

        return payload

    def _get_color(self, threshold_name):
        return THRESHOLD_COLOR.get(threshold_name.upper(), '')

    def _build_ses_reputation_messages(self, threshold_name):
        threshold_name = threshold_name.upper()

        if (threshold_name == THRESHOLD_CRITICAL) or (threshold_name == THRESHOLD_WARNING):
            fallback_message = 'SES account reputation has breached {} threshold.'.format(threshold_name)
            message = 'SES account reputation has breached the {} threshold.'.format(threshold_name)
        elif threshold_name == THRESHOLD_OK:
            fallback_message = 'SES account reputation has recovered.'
            message = 'SES account reputation status is {}.'.format(threshold_name)

        return (fallback_message, message)

    def _enqueue_message(self, message):
        self.messages.append(message)
