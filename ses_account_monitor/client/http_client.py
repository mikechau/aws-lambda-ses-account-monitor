# -*- coding: utf-8 -*-

import logging

from botocore.vendored import requests

from ses_account_monitor.config import LOG_LEVEL
from ses_account_monitor.util import (
    json_dump_request_event,
    json_dump_response_event)


class HttpClient(object):
    '''
    Base HTTP client class.
    '''

    def __init__(self, url, logger=None):
        self.url = url

        self._set_logger(logger)

    @property
    def logger(self):
        return self._logger

    def post_json(self, payload):
        self._log_post_json_request(self.url, payload)

        response = requests.post(
            self.url,
            json=payload)

        self._log_post_json_response(response)

        return response

    def _set_logger(self, logger):
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(self.__module__)
            self._logger.setLevel(LOG_LEVEL)

    def _log_post_json_request(self, url, payload):
        self.logger.debug('Sending POST outbound request to %s', url)

        self.logger.info(
            json_dump_request_event(class_name=self.__class__.__name__,
                                    method_name='post_json',
                                    params=payload,
                                    details={
                                        'url': url
                                    }))

    def _log_post_json_response(self, response):
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
