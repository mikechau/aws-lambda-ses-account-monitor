# -*- coding: utf-8 -*-
import json
from datetime import datetime
from time import mktime


class CustomJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


def json_dump(obj):
    return json.dumps(obj, cls=CustomJsonEncoder)


def json_dump_request_event(class_name, method_name, params=None, details=None):
    event = {
        'class_name': class_name,
        'method_name': method_name,
        'timestamp': datetime.utcnow(),
        'event': 'request',
        'params': params,
        'details':  details
    }

    return json.dumps(event, cls=CustomJsonEncoder)


def json_dump_response_event(class_name, method_name, response=None, details=None):
    event = {
        'class_name': class_name,
        'method_name': method_name,
        'timestamp': datetime.utcnow(),
        'event': 'response',
        'response': response,
        'details':  details
    }

    return json.dumps(event, cls=CustomJsonEncoder)


def unix_timestamp(dt=None):
    _dt = (dt or datetime.utcnow())
    unix = mktime(_dt.timetuple())
    return int(unix)


def iso8601_timestamp(dt=None):
    _dt = (dt or datetime.utcnow())
    return _dt.isoformat()

def current_datetime():
    return datetime.utcnow()
