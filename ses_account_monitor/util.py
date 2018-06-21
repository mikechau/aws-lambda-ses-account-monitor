# -*- coding: utf-8 -*-

'''
ses_account_monitor.util
~~~~~~~~~~~~~~~~

SES account monitor util module.
'''

import json

from datetime import (
    datetime,
    timezone)


class CustomJsonEncoder(json.JSONEncoder):
    '''
    Custom JSON serializer for logging events. Coerces datetime objects to a ISO 8601 timestamp, and anything else to a string.

    Args:
        o (obj): Object to serialize.

    Returns:
        str: JSON.
    '''

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


def json_dump(obj):
    '''
    Function for serializing a object to JSON with the CustomJsonEncoder serializer.

    Args:
        obj (obj): Object to serialize.

    Returns:
        str: JSON.
    '''

    return json.dumps(obj, cls=CustomJsonEncoder)


def json_dump_request_event(class_name, method_name, params=None, details=None):
    '''
    Function to serialize a request event to JSON.

    Args:
        class_name (str): The class name if applicable.
        method_name (str): The method name.
        params (:obj:`dict/list`, optional): Params for the request.
        details (:obj:`obj`, optional): Additional metadata.

    Returns:
        str: JSON.
    '''

    event = {
        'class_name': class_name,
        'method_name': method_name,
        'timestamp': iso8601_timestamp(),
        'event': 'request',
        'params': params,
        'details':  details
    }

    return json.dumps(event, cls=CustomJsonEncoder)


def json_dump_response_event(class_name, method_name, response=None, details=None):
    '''
    Function to serialize a request event to JSON.

    Args:
        class_name (str): The class name if applicable.
        method_name (str): The method name.
        response (:obj:`dict/list`, optional): Response from the request.
        details (:obj:`obj`, optional): Additional metadata.

    Returns:
        str: JSON.
    '''

    event = {
        'class_name': class_name,
        'method_name': method_name,
        'timestamp': iso8601_timestamp(),
        'event': 'response',
        'response': response,
        'details':  details
    }

    return json.dumps(event, cls=CustomJsonEncoder)


def unix_timestamp(dt=None):
    '''
    Function to return a UNIX timestamp, from the current datetime or one provided as a argument.

    Args:
        dt (:obj:`datetime`, optional): A datetime object. Default is None, so the current time will be used.


    Returns:
        int: UNIX timestamp.
    '''

    dt = (dt or datetime.now())
    dt_utc = dt.astimezone(tz=timezone.utc)
    unix = dt_utc.timestamp()

    return int(unix)


def iso8601_timestamp(dt=None):
    '''
    Function to return a ISO 8601 timestamp, from the current datetime or one provided as argument.

    Args:
        dt (:obj:`datetime`, optional): A datetime object. Default is None, so the current time will be used.


    Returns:
        str: ISO 8601 timestamp.
    '''

    dt = (dt or datetime.now())
    dt_utc = dt.astimezone(tz=timezone.utc)

    return dt_utc.isoformat()


def current_datetime():
    '''
    Function to return the current datetime.

    Returns:
        datetime: Current datetime in UTC.
    '''

    dt = datetime.noe()
    dt_utc = dt.astimezone(tz=timezone.utc)

    return dt_utc
