# aws-lambda-ses-account-monitor

[![codecov](https://travis-ci.org/mikechau/aws-lambda-ses-account-monitor.svg?branch=master)](https://travis-ci.org/mikechau/aws-lambda-ses-account-monitor) [![codecov](https://codecov.io/gh/mikechau/aws-lambda-ses-account-monitor/branch/master/graph/badge.svg)](https://codecov.io/gh/mikechau/aws-lambda-ses-account-monitor)

AWS Lambda function for monitoring SES at the account level.

## Development

```shell
git clone https://github.com/mikechau/aws-lambda-ses-account-monitor.git
cd aws-lambda-ses-account-monitor
virtualenv venv -p python3.6
source venv/bin/activate
pip install -r requirements-dev.txt
```

## Testing

```shell
pytest
```

## Building

```shell
make
```

## Versioning

```
# Bump version major
make major

# Bump version minor
make minor

# Bump version patch
make patch
```

A commit incrementing the version will be created as well as the version tag.

The version is saved to [.bumpversion.cfg](./.bumpversion.cfg).

## Deploying

Download the package from [releases](https://github.com/mikechau/aws-lambda-ses-account-monitor/releases) or build it locally. The artifact path locally is at `build/lambda-ses-monitor-account.zip`.

The handler is located at `lambda_handler.lambda_handler`.

## Configuration

| ENVIRONMENT VARIABLE | TYPE | DEFAULT VALUE | CUSTOM EXAMPLE | Description |
| -------------------- | ---- | ------------- | -------------- | ----------- |
| LAMBDA_AWS_ACCOUNT_NAME | `str` | undefined | supercoolco | AWS account name. |
| LAMBDA_AWS_REGION | `str` | undefined | us-west-2 | AWS region. |
| LAMBDA_ENVIRONMENT | `str` | undefined | global | Lambda environment. |
| LAMBDA_NAME | `str` | ses-account-monitor | ses-monitor | Lambda name. |
| LAMBDA_SERVICE_NAME | `str` | $LAMBDA_AWS_ACCOUNT_NAME-$LAMBDA_AWS_REGION-$LAMBDA_ENVIRONMENT-$LAMBDA_NAME | supercoolco-us-west-2-global-ses-account-monitor | Lambda service name, if you want to override the inferred name. |
| LOG_LEVEL | `str` | INFO | WARNING | Log level. |
| MONITOR_SES_REPUTATION | `bool` | `True` | `False` | Flag to monitor SES account reputation. |
| MONITOR_SES_SENDING_QUOTA | `bool` | `True` | `False` | Flag to monitor SES account sending quota. |
| NOTIFY_PAGER_DUTY_ON_SES_REPUTATION | `bool` | `False` | `True` | Flag to enable PagerDuty notifications when SES account reputation reaches thresholds. |
| NOTIFY_PAGER_DUTY_ON_SES_SENDING_QUOTA | `bool` | `False` | `True` |Flag to enable PagerDuty notifications when SES account sending quota reaches thresholds. |
| NOTIFY_SLACK_ON_SES_REPUTATION | `bool` | `False` | `True` | Flag to enable Slack notifications when SES account reputation reaches thresholds. |
| NOTIFY_SLACK_ON_SES_SENDING_QUOTA | `bool` | `False` | `True` | Flag to enable Slack notifications when SES account sending quota reaches thresholds. |
| PAGER_DUTY_EVENTS_URL| `str` | https://events.pagerduty.com/v2/enqueue | - | PagerDuty events url. |
| PAGER_DUTY_ROUTING_KEY | `str` | `None` | abcefg1234567 | PagerDuty routing key. |
| SES_BOUNCE_RATE_CRITICAL_PERCENT | `float` | 8 | 9 | Percentage for critical threshold, AWS suspension is at 10+. |
| SES_BOUNCE_RATE_WARNING_PERCENT | `float` | 5 | 7 | Percentage for warning th reshold, AWS warning recommendation is 5. |
| SES_COMPLAINT_RATE_CRITICAL_PERCENT | `float` | 0.04 | 0.045 | Percentage for critical threshold, AWS suspension is at 0.5+. |
| SES_COMPLAINT_RATE_WARNING_PERCENT | `float` | 0.01 | 0.03 | Percentage for warning threshold, AWS recommendation is at 0.1. |
| SES_SENDING_QUOTA_WARNING_PERCENT | `float` | 80 | 85 | Percentage for warning threshold. |
| SES_SENDING_QUOTA_CRITICAL_PERCENT | `float` | 90 | 95 | Percentage for critical threshold. |
| SES_CONSOLE_URL | `str` | https://$LAMBDA_AWS_REGION.console.aws.amazon.com/ses/?region=$LAMBDA_AWS_REGION | - | SES console url. |
| SES_REPUTATION_DASHBOARD_URL | `str` | - | - | SES reputation dashboard url. |
| SES_REPUTATION_PERIOD | `int` | 900 | 1800 | - | The collection period in seconds. |
| SES_REPUTATION_METRIC_TIMEDELTA | `int` | 1800 | 3600 | Used to calculate the start time for retrieving the metric data. |
| SES_MANAGEMENT_STRATEGY | `str` | alert | managed | Strategy for how to handle metrics at threshold levels. Default is to alert only. Switch to managed to enable SES autopausing. |
| SLACK_CHANNELS | `list` | '' | #general,#dev-ops,#alerts | Comma delimited list of channels to post notifications to. |
| SLACK_FOOTER_ICON_URL | `str` | https://platform.slack-edge.com/img/default_application_icon.png | - | URL for the Slack message footer icon. |
| SLACK_ICON_EMOJI | `str` | None | :dragon: | Slack icon emoji, optional. |
| SLACK_WEBHOOK_URL | `str` | None | https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX | Slack webook url. |

## License

MIT.
