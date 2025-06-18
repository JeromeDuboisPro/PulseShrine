import boto3
from mypy_boto3_dynamodb.service_resource import Table  # type: ignore

from shared.services.aws import get_region_name


def get_start_pulse_table_name() -> str:
    """
    Retrieve the name of the DynamoDB table used for storing pulses.

    Returns:
        str: The name of the DynamoDB table.
    """
    return "StartPulsesTable"  # Replace with your actual table name or configuration retrieval logic


def get_stop_pulse_table_name() -> str:
    """
    Retrieve the name of the DynamoDB table used for storing pulses.

    Returns:
        str: The name of the DynamoDB table.
    """
    return "StopPulsesTable"  # Replace with your actual table name or configuration retrieval logic


def get_ingested_pulse_table_name() -> str:
    """
    Retrieve the name of the DynamoDB table used for storing pulses.

    Returns:
        str: The name of the DynamoDB table.
    """
    return "IngestedPulsesTable"  # Replace with your actual table name or configuration retrieval logic


def create_start_pulse_table() -> Table:
    """Create a mock DynamoDB table for pulse data."""
    dynamodb_resource = boto3.resource("dynamodb", region_name=get_region_name())
    table = dynamodb_resource.create_table(
        TableName=get_start_pulse_table_name(),
        KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Wait for table to be created
    table.wait_until_exists()

    return table


def create_stop_pulse_table() -> Table:
    """Create a mock DynamoDB table for pulse data."""

    dynamodb_resource = boto3.resource("dynamodb", region_name=get_region_name())
    table = dynamodb_resource.create_table(
        TableName=get_stop_pulse_table_name(),
        KeySchema=[{"AttributeName": "pulse_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "pulse_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Wait for table to be created
    table.wait_until_exists()

    return table


def create_ingested_pulse_table() -> Table:
    """Create a mock DynamoDB table for pulse data."""

    dynamodb_resource = boto3.resource("dynamodb", region_name=get_region_name())
    table = dynamodb_resource.create_table(
        TableName=get_ingested_pulse_table_name(),
        KeySchema=[{"AttributeName": "pulse_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "pulse_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Wait for table to be created
    table.wait_until_exists()

    return table
