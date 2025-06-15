import boto3
import os
from boto3.resources.base import ServiceResource
from functools import cache


def get_region_name() -> str:
    """
    Get the AWS region name from the environment variable or default to 'us-east-1'.

    Returns:
        str: The AWS region name.
    """
    return os.getenv("AWS_REGION", "eu-west-3")


@cache
def get_dynamodb_resource() -> ServiceResource:
    """
    Get a DynamoDB resource instance.

    Returns:
        boto3.resources.base.ServiceResource: The DynamoDB resource.
    """
    return boto3.resource("dynamodb", region_name=get_region_name())


@cache
def get_ddb_table(table_name: str):
    return get_dynamodb_resource().Table(table_name)
