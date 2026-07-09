import os

# AWS Region
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# DynamoDB Table Names
DYNAMODB_TABLE_USERS = os.environ.get('DYNAMODB_TABLE_USERS', 'stocker_users')
DYNAMODB_TABLE_PORTFOLIO = os.environ.get('DYNAMODB_TABLE_PORTFOLIO', 'stocker_portfolio')
DYNAMODB_TABLE_ORDERS = os.environ.get('DYNAMODB_TABLE_ORDERS', 'stocker_orders')
DYNAMODB_TABLE_STOCKS = os.environ.get('DYNAMODB_TABLE_STOCKS', 'stocker_stocks')

# AWS Credentials (use IAM role on EC2 — these are fallback for local dev)
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
