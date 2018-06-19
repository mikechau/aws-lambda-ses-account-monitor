# -*- coding: utf-8 -*-
import os

from collections import namedtuple

SlackServiceConfig = namedtuple('SlackServiceConfig', ('action',
                                                       'aws_account_name',
                                                       'aws_environment',
                                                       'aws_region',
                                                       'channels',
                                                       'footer_icon_url',
                                                       'icon_emoji',
                                                       'service_name',
                                                       'ses_console_url',
                                                       'ses_reputation_dashboard_url',
                                                       'webhook_url'))
