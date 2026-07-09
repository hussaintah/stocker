"""
Run once to create all DynamoDB tables for Stocker.
Usage: python setup_dynamodb.py
"""
import boto3
from config.aws_config import AWS_REGION

dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)


def create_table_if_not_exists(name, key_schema, attr_defs, gsi=None):
    try:
        kwargs = {
            'TableName': name,
            'KeySchema': key_schema,
            'AttributeDefinitions': attr_defs,
            'BillingMode': 'PAY_PER_REQUEST',
        }
        if gsi:
            kwargs['GlobalSecondaryIndexes'] = gsi
        dynamodb.create_table(**kwargs)
        print(f'✅ Created table: {name}')
    except dynamodb.exceptions.ResourceInUseException:
        print(f'ℹ️  Table already exists: {name}')


# Users Table
create_table_if_not_exists(
    'stocker_users',
    key_schema=[{'AttributeName': 'UserID', 'KeyType': 'HASH'}],
    attr_defs=[{'AttributeName': 'UserID', 'AttributeType': 'S'}]
)

# Portfolio Table (UserID + symbol as composite key)
create_table_if_not_exists(
    'stocker_portfolio',
    key_schema=[
        {'AttributeName': 'UserID', 'KeyType': 'HASH'},
        {'AttributeName': 'symbol', 'KeyType': 'RANGE'},
    ],
    attr_defs=[
        {'AttributeName': 'UserID', 'AttributeType': 'S'},
        {'AttributeName': 'symbol', 'AttributeType': 'S'},
    ]
)

# Orders Table with GSI on UserID for per-user queries
create_table_if_not_exists(
    'stocker_orders',
    key_schema=[{'AttributeName': 'OrderID', 'KeyType': 'HASH'}],
    attr_defs=[
        {'AttributeName': 'OrderID', 'AttributeType': 'S'},
        {'AttributeName': 'UserID', 'AttributeType': 'S'},
    ],
    gsi=[{
        'IndexName': 'UserID-index',
        'KeySchema': [{'AttributeName': 'UserID', 'KeyType': 'HASH'}],
        'Projection': {'ProjectionType': 'ALL'},
    }]
)

print('\n✅ DynamoDB setup complete.')
