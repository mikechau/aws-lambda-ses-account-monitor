# -*- coding: utf-8 -*-
import os

from collections import namedtuple

# CONTEXT BUILDERS
SlackServiceConfig = namedtuple('SlackServiceConfig', ('aws_account_name',
                                                       'aws_environment',
                                                       'aws_region',
                                                       'footer_icon_url',
                                                       'ses_console_url',
                                                       'ses_reputation_dashboard_url',
                                                       'service_name'))

# STATIC CONSTANTS
THRESHOLD_WARNING = 'WARNING'
THRESHOLD_CRITICAL = 'CRITICAL'
THRESHOLD_OK = 'OK'

# LAMBDA CONSTANTS
LAMBDA_AWS_ACCOUNT_NAME = os.getenv('LAMBDA_AWS_ACCOUNT_NAME', 'undefined')
LAMBDA_AWS_REGION = os.getenv('LAMBDA_AWS_REGION', 'undefined')
LAMBDA_ENVIRONMENT = os.getenv('LAMBDA_ENVIRONMENT', 'undefined')
LAMBDA_NAME = os.getenv('LAMBDA_NAME', 'ses-account-monitor')
LAMBDA_SERVICE_NAME = os.getenv('LAMBDA_SERVICE_NAME', '{account}-{region}-{environment}-{name}'.format(account=LAMBDA_AWS_ACCOUNT_NAME,
                                                                                                        region=LAMBDA_AWS_REGION,
                                                                                                        environment=LAMBDA_ENVIRONMENT,
                                                                                                        name=LAMBDA_NAME))

# LOG CONSTANTS
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# SES CONSTANTS
SES_CONSOLE_URL = os.getenv('SES_CONSOLE_URL',
                            'https://{region}.console.aws.amazon.com/ses/?region={region}'.format(region=LAMBDA_AWS_REGION))
SES_REPUTATION_DASHBOARD_URL = os.getenv('SES_REPUTATION_DASHBOARD_URL', SES_CONSOLE_URL)
SES_REPUTATION_PERIOD = os.getenv('SES_REPUTATION_PERIOD', 900)
SES_REPUTATION_PERIOD_TIMEDELTA = os.getenv('SES_REPUTATION_PERIOD_TIMEDELTA', 1800)

# SLACK CONSTANTS
SLACK_FOOTER_ICON_URL = os.getenv('SLACK_FOOTER_ICON_URL', 'https://platform.slack-edge.com/img/default_application_icon.png')


# SERVICE CONFIGS
SLACK_SERVICE_CONFIG = SlackServiceConfig(aws_account_name=LAMBDA_AWS_ACCOUNT_NAME,
                                          aws_environment=LAMBDA_ENVIRONMENT,
                                          aws_region=LAMBDA_AWS_REGION,
                                          footer_icon_url=SLACK_FOOTER_ICON_URL,
                                          ses_console_url=SES_CONSOLE_URL,
                                          ses_reputation_dashboard_url=SES_REPUTATION_DASHBOARD_URL,
                                          service_name=LAMBDA_SERVICE_NAME)
