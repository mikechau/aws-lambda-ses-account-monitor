# -*- coding: utf-8 -*-

'''
ses_account_monitor.configs.pager_duty_service_config
~~~~~~~~~~~~~~~~

PagerDuty service config module, context used by the PagerDuty service.
'''

from collections import namedtuple


PagerDutyServiceConfig = namedtuple('PagerDutyServiceConfig', ('aws_account_name',
                                                               'aws_environment',
                                                               'aws_region',
                                                               'events_url',
                                                               'routing_key',
                                                               'service_name',
                                                               'ses_console_url',
                                                               'ses_reputation_dashboard_url'))
'''
class:PagerDutyServiceConfig

Args:
    aws_account_name (str): AWS account name. Ex: supercoolco.
    aws_environment (str): AWS environment name. Ex: prod.
    aws_region (str): AWS region. Ex: us-west-2.
    events_url (str): The PagerDuty events url to publish to.
    routing_key (str): The PagerDuty routing key.
    service_name (str): The name of the service. Ex: lambda-ses-account-monitor.
    ses_console_url (str): The SES console url.
    ses_reputation_dashboard_url (str): The SES reputation dashboard url.
'''
