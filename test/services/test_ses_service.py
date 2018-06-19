# -*- coding: utf-8 -*-
from datetime import datetime

import boto3
import pytest

from botocore.stub import Stubber
from ses_account_monitor.services.ses_service import SesService


@pytest.fixture()
def client():
    return boto3.client('ses',
                        aws_access_key_id='a',
                        aws_secret_access_key='b',
                        region_name='us-west-2')


@pytest.fixture()
def service(client):
    return SesService(client=client)


@pytest.fixture()
def ses_quota_responses():
    return (({
        'Max24HourSend': 123.0,
        'MaxSendRate': 523.0,
        'SentLast24Hours': 0.0
    }, 90, False), ({
        'Max24HourSend': 123.0,
        'MaxSendRate': 523.0,
        'SentLast24Hours': 123.0
    }, 80, True), ({
        'Max24HourSend': 123.0,
        'MaxSendRate': 523.0,
        'SentLast24Hours': 150.0
    }, 100, True), ({
        'Max24HourSend': 123.0,
        'MaxSendRate': 523.0,
        'SentLast24Hours': 123.0
    }, None, True))


@pytest.fixture()
def is8601_date():
    return datetime(2018, 1, 1, 0, 0, 0, 0).isoformat()


def test_get_account_sending_quota(client, service, ses_quota_responses):
    stubber = Stubber(client)

    stubber.add_response('get_send_quota',
                         ses_quota_responses[0][0],
                         {})

    with stubber:
        result = service.get_account_sending_quota()

        assert result == {
            'Max24HourSend': 123.0,
            'MaxSendRate': 523.0,
            'SentLast24Hours': 0.0
        }


def test_is_account_sending_rate_over(client, service, ses_quota_responses):
    stubber = Stubber(client)

    for response, percentage, expected_result in ses_quota_responses:
        stubber.add_response('get_send_quota',
                             response,
                             {})
        stubber.activate()

        result = service.is_account_sending_rate_over(percentage)

        stubber.deactivate()

        assert result == expected_result


def test_toggle_account_sending(client, service):
    stubber = Stubber(client)

    stubber.add_response('get_account_sending_enabled',
                         {'Enabled': True},
                         {})
    stubber.add_response('update_account_sending_enabled',
                         {},
                         {'Enabled': False})
    stubber.add_response('get_account_sending_enabled',
                         {'Enabled': False},
                         {})
    stubber.add_response('update_account_sending_enabled',
                         {},
                         {'Enabled': True})

    with stubber:
        disable_result = service.toggle_account_sending()
        assert disable_result is False

        enable_result = service.toggle_account_sending()
        assert enable_result is True


def test_enable_account_sending(client, service):
    stubber = Stubber(client)
    stubber.add_response('update_account_sending_enabled',
                         {},
                         {'Enabled': True})

    with stubber:
        result = service.enable_account_sending()
        assert result is True


def test_disable_account_sending(client, service):
    stubber = Stubber(client)
    stubber.add_response('update_account_sending_enabled',
                         {},
                         {'Enabled': False})

    with stubber:
        result = service.disable_account_sending()
        assert result is False


def test_get_account_sending_current_percentage(client, service):
    stubber = Stubber(client)

    stubber.add_response('get_send_quota',
                         {
                             'Max24HourSend': 10.0,
                             'MaxSendRate': 50.0,
                             'SentLast24Hours': 0.0
                         },
                         {})
    stubber.add_response('get_send_quota',
                         {
                             'Max24HourSend': 123.0,
                             'MaxSendRate': 523.0,
                             'SentLast24Hours': 150.0
                         },
                         {})
    with stubber:
        zero_result = service.get_account_sending_current_percentage()
        assert zero_result == 0

        hundred_result = service.get_account_sending_current_percentage()
        assert hundred_result > 100


def test_get_account_sending_remaining_percentage(client, service):
    stubber = Stubber(client)

    stubber.add_response('get_send_quota',
                         {
                             'Max24HourSend': 10.0,
                             'MaxSendRate': 50.0,
                             'SentLast24Hours': 0.0
                         },
                         {})
    stubber.add_response('get_send_quota',
                         {
                             'Max24HourSend': 123.0,
                             'MaxSendRate': 523.0,
                             'SentLast24Hours': 150.0
                         },
                         {})
    with stubber:
        hundred_result = service.get_account_sending_remaining_percentage()
        assert hundred_result == 100

        zero_result = service.get_account_sending_remaining_percentage()
        assert zero_result == 0


def test_get_account_sending_stats(client, service, is8601_date):
    stubber = Stubber(client)

    stubber.add_response('get_send_quota',
                         {
                             'Max24HourSend': 50.0,
                             'MaxSendRate': 50.0,
                             'SentLast24Hours': 10.0
                         },
                         {})

    with stubber:
        result = service.get_account_sending_stats(ts=is8601_date)

        assert result == (10.0, 50.0, 20.0, '2018-01-01T00:00:00')
