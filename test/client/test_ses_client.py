# -*- coding: utf-8 -*-
import boto3
import pytest

from botocore.stub import Stubber
from ses_account_monitor.client.ses_client import SesClient


@pytest.fixture()
def ses_client():
    return boto3.client('ses',
                        aws_access_key_id='a',
                        aws_secret_access_key='b',
                        region_name='us-west-2')


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


def test_get_account_sending_quota(ses_client, ses_quota_responses):
    stubber = Stubber(ses_client)

    stubber.add_response('get_send_quota',
                         ses_quota_responses[0][0],
                         {})
    stubber.activate()

    client = SesClient(client=ses_client)
    results = client.get_account_sending_quota()

    assert results == {
        'Max24HourSend': 123.0,
        'MaxSendRate': 523.0,
        'SentLast24Hours': 0.0
    }


def test_is_account_sending_rate_over(ses_client, ses_quota_responses):
    stubber = Stubber(ses_client)
    client = SesClient(client=ses_client)

    for response, percentage, expected_result in ses_quota_responses:
        stubber.add_response('get_send_quota',
                             response,
                             {})
        stubber.activate()

        results = client.is_account_sending_rate_over(percentage)

        stubber.deactivate()

        assert results == expected_result


def test_toggle_account_sending(ses_client):
    stubber = Stubber(ses_client)

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
        client = SesClient(client=ses_client)

        disable_response = client.toggle_account_sending()
        assert disable_response is False

        enable_response = client.toggle_account_sending()
        assert enable_response is True


def test_enable_account_sending(ses_client):
    stubber = Stubber(ses_client)
    stubber.add_response('update_account_sending_enabled',
                         {},
                         {'Enabled': True})
    stubber.activate()

    client = SesClient(client=ses_client)
    response = client.enable_account_sending()

    assert response is True


def test_disable_account_sending(ses_client):
    stubber = Stubber(ses_client)
    stubber.add_response('update_account_sending_enabled',
                         {},
                         {'Enabled': False})
    stubber.activate()

    client = SesClient(client=ses_client)
    response = client.disable_account_sending()

    assert response is False


def test_get_account_sending_current_percentage(ses_client):
    stubber = Stubber(ses_client)
    client = SesClient(client=ses_client)

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
        zero_response = client.get_account_sending_current_percentage()
        assert zero_response == 0

        hundred_response = client.get_account_sending_current_percentage()
        assert hundred_response == 100


def test_get_account_sending_remaining_percentage(ses_client):
    stubber = Stubber(ses_client)
    client = SesClient(client=ses_client)

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
        hundred_response = client.get_account_sending_remaining_percentage()
        assert hundred_response == 100

        zero_response = client.get_account_sending_remaining_percentage()
        assert zero_response == 0
