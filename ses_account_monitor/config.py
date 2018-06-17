import os

LAMBDA_AWS_ACCOUNT_NAME = os.getenv('LAMBDA_AWS_ACCOUNT_NAME', 'undefined')
LAMBDA_AWS_REGION = os.getenv('LAMBDA_AWS_REGION', 'undefined')
LAMBDA_NAME = os.getenv('LAMBDA_NAME', 'SES Account Monitor')
LAMBDA_ENVIRONMENT = os.getenv('LAMBDA_ENVIRONMENT', 'undefined')

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
