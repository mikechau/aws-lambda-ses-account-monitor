# -*- coding: utf-8 -*-

'''
ses_account_monitor.configs.slack_service_config
~~~~~~~~~~~~~~~~

Slack service config module, context used by the Slack service.
'''

from collections import namedtuple

SlackServiceConfig = namedtuple('SlackServiceConfig', ('aws_account_name',
                                                       'aws_environment',
                                                       'aws_region',
                                                       'channels',
                                                       'footer_icon_url',
                                                       'icon_emoji',
                                                       'service_name',
                                                       'ses_console_url',
                                                       'ses_reputation_dashboard_url',
                                                       'webhook_url'))
'''
class:SlackServiceConfig

Args:
    aws_account_name (str): AWS account name. Ex: supercoolco.
    aws_environment (str): AWS environment name. Ex: prod.
    aws_region (str): AWS region. Ex: us-west-2.
    channels (list): List of channels to post to. Ex: ['#alerts']
    footer_icon_url (str/NoneType): Slack footer icon url.
    icon_emoji (str/NoneType): Slack icon emoji.
    service_name (str): The name of the service. Ex: lambda-ses-account-monitor.
    ses_console_url (str): The SES console url.
    ses_reputation_dashboard_url (str): The SES reputation dashboard url.
    webhook_url (str): The Slack webhook url to post messages to.
'''
