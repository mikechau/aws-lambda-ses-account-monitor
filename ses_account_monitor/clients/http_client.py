# -*- coding: utf-8 -*-

'''
ses_account_monitor.clients.http_client
~~~~~~~~~~~~~~~~

HTTP client module, it's a wrapper around requests.
'''

import logging

from botocore.vendored import requests

from ses_account_monitor.util import (
    json_dump_request_event,
    json_dump_response_event)


class HttpClient(object):
    '''
    HttpClient class, used as a base class.
    '''

    def __init__(self, url, logger=None):
        '''
        Args:
            url (str): Event triggering the function.
            logger (:obj:`logging.Logger`, optional): Logger instance. Defaults to None, which will create a logger instance.
        '''

        self._logger = (logger or self._build_logger())
        self.url = url

    @property
    def logger(self):
        '''
        obj (logger.Logger): The logger instance.
        '''

        return self._logger

    def post_json(self, payload):
        '''
        Sends a JSON payload via the requests http client module.

        Args:
            payload (dict): Dict containing the POST params.

        Returns:
            response (requests.Response): Response object.
        '''

        self._log_post_json_request(self.url, payload)

        response = requests.post(
            self.url,
            json=payload)

        self._log_post_json_response(response)

        return response

    def _build_logger(self):
        '''
        Builds a logger instance.
        '''

        logger = logging.getLogger(self.__module__)
        logger.addHandler(logging.NullHandler())
        return logger

    def _log_post_json_request(self, url, payload):
        '''
        Logs JSON POST params.

        Args:
            url (str): The url being posted to.
            payload (dict): Dict containing the POST params.
        '''

        self.logger.debug('Sending POST outbound request to %s', url)

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name__,
                                    method_name='post_json',
                                    params=payload,
                                    details={
                                        'url': url
                                    }))

    def _log_post_json_response(self, response):
        '''
        Logs JSON POST params.

        Args:
            url (str): The url being posted to.
            response (requests.Response): Response object.
        '''

        self.logger.debug('Received POST %s response from %s',
                          response.status_code,
                          response.url)

        self.logger.info(
            json_dump_response_event(class_name=self.__class__.__name__,
                                     method_name='post_json',
                                     response=response.json(),
                                     details={
                                        'url': response.url,
                                        'status_code': response.status_code
                                     }))
