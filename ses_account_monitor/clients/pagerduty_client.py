# -*- coding: utf-8 -*-
from ses_account_monitor.clients.http_client import HttpClient


class PagerDutyClient(HttpClient):
    '''
    Send events to PagerDuty.
    '''
