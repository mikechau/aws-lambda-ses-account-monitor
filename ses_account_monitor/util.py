# -*- coding: utf-8 -*-
import json


class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super(DatetimeEncoder, obj).default(obj)
        except TypeError:
            return str(obj)


def json_dump(obj):
    return json.dumps(obj, cls=DatetimeEncoder)
