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
