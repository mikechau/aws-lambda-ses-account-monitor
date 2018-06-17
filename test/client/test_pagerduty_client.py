# -*- coding: utf-8 -*-
import pytest
import responses

from ses_account_monitor.client.pagerduty_client import PagerDutyClient


@pytest.fixture()
def webhook_url():
    return 'https://events.pagerduty.com/v2/enqueue'


@pytest.fixture()
def client(webhook_url):
    pagerduty_client = PagerDutyClient(webhook_url)
    pagerduty_client.logger.setLevel('INFO')
    return pagerduty_client


@pytest.fixture()
def trigger_payload():
    return {
        'payload': {
            'summary': 'Example alert on host1.example.com',
            'timestamp': '2015-07-17T08:42:58.315+0000',
            'source': 'monitoringtool:cloudvendor:central-region-dc-01:852559987:cluster/api-stats-prod-003',
            'severity': 'info',
            'component': 'postgres',
            'group': 'prod-datapipe',
            'class': 'deploy',
            'custom_details': {
                'ping time': '1500ms',
                'load avg': 0.75
            }
        },
        'routing_key': 'samplekeyhere',
        'dedup_key': 'samplekeyhere',
        'images': [{
            'src': 'https://www.pagerduty.com/wp-content/uploads/2016/05/pagerduty-logo-green.png',
            'href': 'https://example.com/',
            'alt': 'Example text'
        }],
        'links': [{
            'href': 'https://example.com/',
            'text': 'Link text'
        }],
        'event_action': 'trigger',
        'client': 'Sample Monitoring Service',
        'client_url': 'https://monitoring.example.com'
    }


@responses.activate
def test_post_message(client, webhook_url, trigger_payload):
    with responses.RequestsMock(target='botocore.vendored.requests.adapters.HTTPAdapter.send') as rsps:
        rsps.add(
            responses.POST,
            webhook_url,
            status=202,
            json={
                'status': 'success',
                'message': 'Event processed',
                'dedup_key': 'samplekeyhere'
            }
        )

        response = client.post_json(trigger_payload)

        assert response.status_code == 202
