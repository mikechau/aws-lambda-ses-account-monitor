# -*- coding: utf-8 -*-
import pytest
import responses

from ses_account_monitor.client.slack_client import SlackClient


@pytest.fixture()
def webhook_url():
    return 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'


@pytest.fixture()
def client(webhook_url):
    slack_client = SlackClient(webhook_url)
    slack_client.logger.setLevel('DEBUG')
    return slack_client


@pytest.fixture()
def message_payload():
    return {
        'text': 'Robert DeSoto added a new task',
        'attachments': [
            {
                'fallback': 'Plan a vacation',
                'author_name': 'Owner: rdesoto',
                'title': 'Plan a vacation',
                'text': 'I have been working too hard, it is time for a break.',
                'actions': [
                    {
                        'name': 'action',
                        'type': 'button',
                        'text': 'Complete this task',
                        'style': '',
                        'value': 'complete'
                    },
                    {
                        'name': 'tags_list',
                        'type': 'select',
                        'text': 'Add a tag...',
                        'data_source': 'static',
                        'options': [
                            {
                                'text': 'Launch Blocking',
                                'value': 'launch-blocking'
                            },
                            {
                                'text': 'Enhancement',
                                'value': 'enhancement'
                            },
                            {
                                'text': 'Bug',
                                'value': 'bug'
                            }
                        ]
                    }
                ]
            }
        ]
    }


@responses.activate
def test_post_message(client, webhook_url, message_payload):
    with responses.RequestsMock(target='botocore.vendored.requests.adapters.HTTPAdapter.send') as rsps:
        rsps.add(
            responses.POST,
            webhook_url,
            status=200,
            json={
                'ok': True
            }
        )

        response = client.post_json(message_payload)

        assert response.status_code == 200
