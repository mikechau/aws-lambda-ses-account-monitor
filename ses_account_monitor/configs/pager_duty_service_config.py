# -*- coding: utf-8 -*-
from collections import namedtuple

PagerDutyServiceConfig = namedtuple('PagerDutyServiceConfig', ('action',
                                                               'aws_account_name',
                                                               'aws_environment',
                                                               'aws_region',
                                                               'events_url',
                                                               'routing_key',
                                                               'service_name',
                                                               'ses_console_url',
                                                               'ses_reputation_dashboard_url'))
