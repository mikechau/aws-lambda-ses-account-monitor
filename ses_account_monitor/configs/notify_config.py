# -*- coding: utf-8 -*-

'''
ses_account_monitor.config.notify_config
~~~~~~~~~~~~~~~~

Notify config module, flags for when to send event notifications.
'''

from collections import namedtuple


NotifyConfig = namedtuple('NotifyConfig', ('notify_pager_duty_on_ses_reputation',
                                           'notify_pager_duty_on_ses_sending_quota',
                                           'notify_slack_on_ses_reputation',
                                           'notify_slack_on_ses_sending_quota'))
'''
class:NotifyConfig

Args:
    notify_pager_duty_on_ses_reputation (bool): Flag to enable SES reputation notifications to Pager Duty.
    notify_pager_duty_on_ses_sending_quota (bool): Flag to enable SES sending quota notifications to Pager Duty.
    notify_slack_on_ses_reputation (bool): Flag to enable SES reputation notifications to Slack.
    notify_slack_on_ses_sending_quota (bool): Flag to enable SES sending quota notifications to Slack.
'''
