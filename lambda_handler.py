# -*- coding: utf-8 -*-

'''
AWS Lambda function handler.
'''

import logging

import boto3

from ses_account_monitor.config import (
    LAMBDA_AWS_SESSION_CONFIG,
    LOG_LEVEL)
from ses_account_monitor.monitor import Monitor
from ses_account_monitor.util import (
    json_dump_request_event,
    json_dump_response_event)


logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

session = boto3.Session(**LAMBDA_AWS_SESSION_CONFIG)
ses_client = session.client('ses')
cloudwatch_client = session.client('cloudwatch')


def lambda_handler(event, context):
    '''
    Args:
        event (dict/list/str/int/float/NoneType): AWS event data.
        context (LambdaContext): Lambda runtime information.
    '''

    logger.debug('Lambda event received.')
    logger.info(json_dump_request_event(class_name='lambda_handler',
                                        method_name='lambda_handler',
                                        params=event,
                                        details={
                                            'message': 'Lambda event received.'}))

    monitor = Monitor(ses_client=ses_client,
                      cloudwatch_client=cloudwatch_client,
                      logger=logger)
    monitor.handle_ses_sending_quota()
    monitor.handle_ses_reputation()

    response = monitor.send_notifications(raise_on_errors=True)

    logger.debug('Lambda event processed.')
    logger.info(json_dump_response_event(class_name='lambda_handler',
                                         method_name='lambda_handler',
                                         response=response,
                                         details={
                                            'message': 'Lambda event processed.'}))
