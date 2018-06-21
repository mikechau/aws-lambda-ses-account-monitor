# -*- coding: utf-8 -*-

'''
ses_account_monitor.services.slack_service
~~~~~~~~~~~~~~~~

Slack service module.
'''

from __future__ import division

from collections import deque

from ses_account_monitor.clients.http_client import HttpClient

from ses_account_monitor.config import (
    ACTION_ALERT,
    NOTIFY_DRY_RUN,
    SLACK_SERVICE_CONFIG,
    THRESHOLD_CRITICAL,
    THRESHOLD_OK,
    THRESHOLD_WARNING)

from ses_account_monitor.util import (
    iso8601_timestamp,
    unix_timestamp)

THRESHOLD_COLOR = {
    THRESHOLD_CRITICAL: 'danger',
    THRESHOLD_OK: 'ok',
    THRESHOLD_WARNING: 'warning'
}


def get_color(threshold_name):
    '''
    Get the Slack color based on the threshold name.

    Args:
        threshold_name (str): Threshold name. Ex: CRITICAL, WARNING, OK.

    Returns:
        str: The Slack color.
    '''

    return THRESHOLD_COLOR.get(threshold_name.upper(), '')


def build_ses_reputation_text(threshold_name):
    '''
    Generate the SES reputation text, returns the fallback text and primary text.

    Args:
        threshold_name (str): Threshold name. Ex: CRITICAL, WARNING, OK.

    Returns:
        tuple: The fallback text and primary text.
            fallback_text (str): Slack fallback message text.
            primary_text (str): Slack primary message text.
    '''

    threshold_name = threshold_name.upper()

    if (threshold_name == THRESHOLD_CRITICAL) or (threshold_name == THRESHOLD_WARNING):
        fallback_text = 'SES account reputation has breached {} threshold.'.format(threshold_name)
        primary_text = 'SES account reputation has breached the {} threshold.'.format(threshold_name)
    elif threshold_name == THRESHOLD_OK:
        fallback_text = 'SES account reputation has recovered.'
        primary_text = 'SES account reputation status is {}.'.format(threshold_name)

    return (fallback_text, primary_text)


class SlackService(HttpClient):
    '''
    Slack service class, inherits HttpClient.
    '''

    def __init__(self,
                 url=None,
                 channels=None,
                 config=None,
                 dry_run=False,
                 logger=None):
        '''
        Args:
            url (str): The Slack webhook url.
            channels (:obj:`list` of :obj:`str`): Slack channels to send messages to.
            config (:obj:`SlackServiceConfig`, optional): Slack service configuration object.
            dry_run (:obj:`bool`, optional): Disable making live API calls. Defaults to False (make live API calls).
            logger (:obj:`logging.Logger`, optional): Logger instance. Defaults to None, which will create a logger instance.
        '''

        self._config = (config or SLACK_SERVICE_CONFIG)
        self._dry_run = (dry_run or NOTIFY_DRY_RUN)

        if url is None:
            url = self._config.webhook_url

        super(SlackService, self).__init__(url=url,
                                           logger=logger)

        self.messages = deque([])
        self.channels = (channels or self._config.channels)
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

    def send_notifications(self, dry_run=None):
        '''
        Send all messages in the queue to Slack.

        Args:
            dry_run (:obj:`bool`, optional): Disable making live API calls. Defaults to False (make live API calls).

        Returns:
            tuple:
                send_status (bool): Returns True when notifications were actually sent, if False a dry run was executed.
                responses (:obj:`list` of :obj:`tuple`):
                    channel (str): The Slack channel the message was sent to.
                    responses (:obj:`list` of :obj:`requests.Response/dict`): List of response objects.
                        If a dry run occurred, will return dict objects containing the params for the request.
        '''

        self.logger.debug('Sending notifications to Slack channels...')
        self.logger.debug('Slack channel count: %s', len(self.channels))

        self.responses = []
        send_status = (not dry_run)

        if dry_run or self.dry_run:
            self.logger.debug('Slack DRY RUN enabled, not sending notifications!')

            while self.messages:
                message = self.messages.popleft()

                channel_messages = self._build_message_with_channels(message)
                self.responses.extend(channel_messages)

            return self.responses

        while self.messages:
            message = self.messages.popleft()

            for channel in self.channels:
                self.logger.debug('Sending Slack notification to %s...', channel)

                payload = {'channel': channel}
                payload.update(message)

                response = self.post_json(payload=message)
                self.responses.append((channel, response))

        return (send_status, self.responses)

    def enqueue_ses_account_sending_quota_message(self, *args, **kwargs):
        '''
        Adds a SES account sending quota message to the messages queue.

        Args:
            threshold_name (str): The threshold name. Ex: WARNING, CRITICAL.
            threshold_percent (float/int): The threshold percent. Ex: 80% is 80.
            utilization_percent (float/int): The utilization percent. Ex: 80% is 80.
            volume (float/int): The number of emails sent.
            max_volume (float/int): The max number of emails allowed to send.
            metric_iso_ts (:obj:`str`, optional): ISO 8601 timestamp.
            event_unix_ts (:obj:`str/int`, optional): UNIX timestamp.

        Returns:
            self (SlackService): SlackService instance.
        '''

        message = self.build_ses_account_sending_quota_payload(*args, **kwargs)
        self._enqueue_message(message)
        return self

    def enqueue_ses_account_reputation_message(self, *args, **kwargs):
        '''
        Adds a SES account reputation message to the messages queue.

        Args:
            threshold_name (str): The threshold name. Ex: WARNING, CRITICAL.
            metrics (:obj:`list` of :obj:`tuple`): List of tuples containing the metrics.
            event_unix_ts (:obj:`str`, optional): UNIX timestamp of when the event occurred.
                Default is None, which will cause the current time to be used.
            action (:obj:`str`, optional): The action taken in response to the event. Ex: alert, disable, enable.
                Default is None.

        Returns:
            self (SlackService): SlackService instance.
        '''

        message = self.build_ses_account_reputation_payload(*args, **kwargs)
        self._enqueue_message(message)
        return self

    def build_ses_account_sending_quota_payload(self,
                                                threshold_name,
                                                utilization_percent,
                                                threshold_percent,
                                                volume,
                                                max_volume,
                                                metric_iso_ts=None,
                                                event_unix_ts=None):
        '''
        Generate a message payload for SES account sending quota.

        Args:
            threshold_name (str): The threshold name. Ex: WARNING, CRITICAL.
            threshold_percent (float/int): The threshold percent. Ex: 80% is 80.
            utilization_percent (float/int): The utilization percent. Ex: 80% is 80.
            volume (float/int): The number of emails sent.
            max_volume (float/int): The max number of emails allowed to send.
            metric_iso_ts (:obj:`str`, optional): ISO 8601 timestamp.
            event_unix_ts (:obj:`str/int`, optional): UNIX timestamp.

        Returns:
            dict: Slack message payload without the channel.
                attachments (:obj:`list` of :obj:`dict`): Components of the Slack message.
                icon_emoji (str/NoneType): Icon emoji to use from config.
                username (str): Slack username.
        '''

        payload = {
            'attachments': [{
                'fallback': 'SES account sending rate has breached {} threshold.'.format(threshold_name),
                'color': get_color(threshold_name),
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
                        'title': 'Time',
                        'value': (metric_iso_ts or iso8601_timestamp())
                    },
                    {
                        'title': 'Utilization',
                        'value': '{:.2%}'.format(utilization_percent / 100),
                        'short': True
                    },
                    {
                        'title': 'Threshold',
                        'value': '{:.2%}'.format(threshold_percent / 100),
                        'short': True
                    },
                    {
                        'title': 'Volume',
                        'value': volume,
                        'short': True
                    },
                    {
                        'title': 'Max Volume',
                        'value': max_volume,
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
                'ts': (event_unix_ts or unix_timestamp())
            }],
            'icon_emoji': self.config.icon_emoji,
            'username': 'SES Account Monitor'
        }

        return payload

    def build_ses_account_reputation_payload(self,
                                             threshold_name,
                                             metrics,
                                             event_unix_ts=None,
                                             action=None):
        '''
        Generate a message payload for SES account reputation.

        Args:
            threshold_name (str): The threshold name. Ex: WARNING, CRITICAL.
            metrics (:obj:`list` of :obj:`tuple`): List of tuples containing the metrics.
            event_unix_ts (:obj:`str`, optional): UNIX timestamp of when the event occurred.
                Default is None, which will cause the current time to be used.
            action (:obj:`str`, optional): The action taken in response to the event. Ex: alert, disable, enable.
                Default is None.

        Returns:
            dict: Slack message payload without the channel.
                attachments (:obj:`list` of :obj:`dict`): Components of the Slack message.
                icon_emoji (str/NoneType): Icon emoji to use from config.
                username (str): Slack username.
        '''

        fallback_text, primary_text = build_ses_reputation_text(threshold_name)

        message = {
            'attachments': [
                {
                    'fallback': fallback_text,
                    'color': get_color(threshold_name),
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
                    'ts': (event_unix_ts or unix_timestamp())
                }
            ],
            'icon_emoji': self.config.icon_emoji,
            'username': 'SES Account Monitor'
        }

        for label, utilization_percent, threshold_percent, ts in metrics:
            metric_value = '{utilization:.2%} / {threshold:.2%}'.format(utilization=(utilization_percent / 100),
                                                                        threshold=(threshold_percent / 100))

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

    def _build_message_with_channels(self, base_payload):
        '''
        Generate Slack messages, by taking a payload and injecting the channel.

        Args:
            base_payload (dict): The Slack payload to send.

        Returns:
            dict: Slack message payload with the channel.
                attachments (:obj:`list` of :obj:`dict`): Components of the Slack message.
                channel (str): Slack channel.
                icon_emoji (str/NoneType): Icon emoji to use from config.
                username (str): Slack username.
        '''

        messages = []
        for channel in self.channels:
            payload = {'channel': channel}
            payload.update(base_payload)
            messages.append(payload)

        return messages

    def _enqueue_message(self, message):
        '''
        Add a single event to the events queue.
        '''

        self.messages.append(message)
