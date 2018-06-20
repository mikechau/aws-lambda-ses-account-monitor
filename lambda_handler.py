# -*- coding: utf-8 -*-

import logging

from ses_account_monitor.config import LOG_LEVEL
from ses_account_monitor.monitor import Monitor
from ses_account_monitor.util import (
    json_dump_request_event,
    json_dump_response_event
)


logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


def lambda_handler(event, context):
    logger.info(json_dump_request_event(class_name='lambda_handler',
                                        method_name='lambda_handler',
                                        params=event))

    monitor = Monitor()
    monitor.handle_ses_sending_quota()
    monitor.handle_ses_reputation()

    response = monitor.send_notifications(raise_on_errors=True)

    logger.info(json_dump_response_event(class_name='lambda_handler',
                                         method_name='lambda_handler',
                                         response=response))
