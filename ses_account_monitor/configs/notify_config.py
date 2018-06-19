# -*- coding: utf-8 -*-
from collections import namedtuple

NotifyConfig = namedtuple('NotifyConfig', ('notify_pager_duty_on_ses_reputation',
                                           'notify_pager_duty_on_ses_sending_quota',
                                           'notify_slack_on_ses_reputation',
                                           'notify_slack_on_ses_sending_quota',
                                           'strategy'))
