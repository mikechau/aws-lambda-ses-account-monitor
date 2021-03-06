# -*- coding: utf-8 -*-

'''
ses_account_monitor.config
~~~~~~~~~~~~~~~~

SES account monitor config module.
'''

import os

from distutils.util import strtobool

from ses_account_monitor.configs import (
    NotifyConfig,
    PagerDutyServiceConfig,
    SlackServiceConfig)


# STATIC CONSTANTS
ACTION_ALERT = 'alert'
ACTION_PAUSE = 'pause'
ACTION_UNPAUSE = 'unpause'
ACTION_ENABLE = 'enable'
ACTION_DISABLE = 'disable'

SES_MONITOR_STRATEGY_MANAGED = 'managed'
SES_MONITOR_STRATEGY_ALERT = 'alert'

THRESHOLD_CRITICAL = 'CRITICAL'
THRESHOLD_OK = 'OK'
THRESHOLD_WARNING = 'WARNING'

# LAMBDA CONSTANTS
LAMBDA_AWS_ACCOUNT_NAME = os.getenv('LAMBDA_AWS_ACCOUNT_NAME', 'undefined')
LAMBDA_AWS_REGION = os.getenv('LAMBDA_AWS_REGION', os.getenv('AWS_DEFAULT_REGION', None))
LAMBDA_AWS_SESSION_CONFIG = {
    'region_name': LAMBDA_AWS_REGION
}
LAMBDA_ENVIRONMENT = os.getenv('LAMBDA_ENVIRONMENT', 'undefined')
LAMBDA_NAME = os.getenv('LAMBDA_NAME', 'ses-account-monitor')
LAMBDA_SERVICE_NAME = os.getenv('LAMBDA_SERVICE_NAME',
                                '{account}-{region}-{environment}-{name}'.format(account=LAMBDA_AWS_ACCOUNT_NAME,
                                                                                 region=LAMBDA_AWS_REGION,
                                                                                 environment=LAMBDA_ENVIRONMENT,
                                                                                 name=LAMBDA_NAME))

# LOG CONSTANTS
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# MONITOR CONSTANTS
MONITOR_SES_REPUTATION = strtobool(os.getenv('MONITOR_SES_REPUTATION', 'True'))
MONITOR_SES_SENDING_QUOTA = strtobool(os.getenv('MONITOR_SES_SENDING_QUOTA', 'True'))

# NOTIFY CONSTANTS
NOTIFY_DRY_RUN = strtobool(os.getenv('NOTIFY_DRY_RUN', 'False'))
NOTIFY_PAGER_DUTY_ON_SES_REPUTATION = strtobool(os.getenv('NOTIFY_PAGER_DUTY_ON_SES_REPUTATION', 'False'))
NOTIFY_PAGER_DUTY_ON_SES_SENDING_QUOTA = strtobool(os.getenv('NOTIFY_PAGER_DUTY_ON_SES_SENDING_QUOTA', 'False'))
NOTIFY_SLACK_ON_SES_REPUTATION = strtobool(os.getenv('NOTIFY_SLACK_ON_SES_REPUTATION', 'False'))
NOTIFY_SLACK_ON_SES_SENDING_QUOTA = strtobool(os.getenv('NOTIFY_SLACK_ON_SES_SENDING_QUOTA', 'False'))

# PAGERDUTY CONSTANTS
PAGER_DUTY_EVENTS_URL = os.getenv('PAGER_DUTY_EVENTS_URL', 'https://events.pagerduty.com/v2/enqueue')
PAGER_DUTY_ROUTING_KEY = os.getenv('PAGER_DUTY_ROUTING_KEY', None)

# SES CONSTANTS
SES_BOUNCE_RATE_CRITICAL_PERCENT = float(os.getenv('SES_BOUNCE_RATE_CRITICAL_PERCENT', 8))
SES_BOUNCE_RATE_WARNING_PERCENT = float(os.getenv('SES_BOUNCE_RATE_WARNING_PERCENT', 5))

SES_COMPLAINT_RATE_CRITICAL_PERCENT = float(os.getenv('SES_COMPLAINT_RATE_CRITICAL_PERCENT', 0.04))
SES_COMPLAINT_RATE_WARNING_PERCENT = float(os.getenv('SES_COMPLAINT_RATE_WARNING_PERCENT', 0.01))

SES_SENDING_QUOTA_WARNING_PERCENT = float(os.getenv('SES_SENDING_QUOTA_WARNING_PERCENT', 80))
SES_SENDING_QUOTA_CRITICAL_PERCENT = float(os.getenv('SES_SENDING_QUOTA_CRITICAL_PERCENT', 90))

SES_BASE_URL = 'https://{region}.console.aws.amazon.com/ses/home?region={region}'.format(region=LAMBDA_AWS_REGION)

SES_CONSOLE_URL = os.getenv('SES_CONSOLE_URL', '{}#dashboard:'.format(SES_BASE_URL))
SES_REPUTATION_DASHBOARD_URL = os.getenv('SES_REPUTATION_DASHBOARD_URL', '{}#reputation-dashboard:'.format(SES_BASE_URL))

SES_REPUTATION_PERIOD = int(os.getenv('SES_REPUTATION_PERIOD', 900))
SES_REPUTATION_METRIC_TIMEDELTA = int(os.getenv('SES_REPUTATION_METRIC_TIMEDELTA', 1800))

SES_MONITOR_STRATEGY = os.getenv('SES_MONITOR_STRATEGY', SES_MONITOR_STRATEGY_ALERT)

SES_THRESHOLDS = {
    THRESHOLD_CRITICAL: {
        'bounce_rate': SES_BOUNCE_RATE_CRITICAL_PERCENT,
        'complaint_rate': SES_COMPLAINT_RATE_CRITICAL_PERCENT,
        'sending_quota': SES_SENDING_QUOTA_CRITICAL_PERCENT
    },
    THRESHOLD_WARNING: {
        'bounce_rate': SES_BOUNCE_RATE_WARNING_PERCENT,
        'complaint_rate': SES_COMPLAINT_RATE_WARNING_PERCENT,
        'sending_quota': SES_SENDING_QUOTA_WARNING_PERCENT
    }
}

# SLACK CONSTANTS
SLACK_CHANNELS = list(filter(None, os.getenv('SLACK_CHANNELS', '').split(',')))
SLACK_FOOTER_ICON_URL = os.getenv('SLACK_FOOTER_ICON_URL', 'https://platform.slack-edge.com/img/default_application_icon.png')
SLACK_ICON_EMOJI = os.getenv('SLACK_ICON_EMOJI', None)
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', None)

# CONFIGS
NOTIFY_CONFIG = NotifyConfig(notify_pager_duty_on_ses_reputation=NOTIFY_PAGER_DUTY_ON_SES_REPUTATION,
                             notify_pager_duty_on_ses_sending_quota=NOTIFY_PAGER_DUTY_ON_SES_SENDING_QUOTA,
                             notify_slack_on_ses_reputation=NOTIFY_SLACK_ON_SES_REPUTATION,
                             notify_slack_on_ses_sending_quota=NOTIFY_SLACK_ON_SES_SENDING_QUOTA)

PAGER_DUTY_SERVICE_CONFIG = PagerDutyServiceConfig(aws_account_name=LAMBDA_AWS_ACCOUNT_NAME,
                                                   aws_environment=LAMBDA_ENVIRONMENT,
                                                   aws_region=LAMBDA_AWS_REGION,
                                                   events_url=PAGER_DUTY_EVENTS_URL,
                                                   routing_key=PAGER_DUTY_ROUTING_KEY,
                                                   service_name=LAMBDA_SERVICE_NAME,
                                                   ses_console_url=SES_CONSOLE_URL,
                                                   ses_reputation_dashboard_url=SES_REPUTATION_DASHBOARD_URL)

SLACK_SERVICE_CONFIG = SlackServiceConfig(aws_account_name=LAMBDA_AWS_ACCOUNT_NAME,
                                          aws_environment=LAMBDA_ENVIRONMENT,
                                          aws_region=LAMBDA_AWS_REGION,
                                          channels=SLACK_CHANNELS,
                                          footer_icon_url=SLACK_FOOTER_ICON_URL,
                                          icon_emoji=SLACK_ICON_EMOJI,
                                          ses_console_url=SES_CONSOLE_URL,
                                          ses_reputation_dashboard_url=SES_REPUTATION_DASHBOARD_URL,
                                          service_name=LAMBDA_SERVICE_NAME,
                                          webhook_url=SLACK_WEBHOOK_URL)
