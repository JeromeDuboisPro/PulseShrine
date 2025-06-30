from typing import Any
import boto3
import os
from boto3.resources.base import ServiceResource
from functools import cache


def get_region_name() -> str:
    """
    Get the AWS region name from environment variable.
    Uses AWS_REGION if set, otherwise lets boto3 use its default region resolution.

    Returns:
        str: The AWS region name or None to let boto3 handle region resolution.
    """
    # Let boto3 handle region resolution if AWS_REGION is not explicitly set
    # This will use AWS credentials, config files, instance metadata, etc.
    return os.getenv("AWS_REGION")


@cache
def get_dynamodb_resource() -> ServiceResource:
    """
    Get a DynamoDB resource instance.

    Returns:
        boto3.resources.base.ServiceResource: The DynamoDB resource.
    """
    region = get_region_name()
    if region:
        return boto3.resource("dynamodb", region_name=region)
    else:
        # Let boto3 use default region resolution
        return boto3.resource("dynamodb")


@cache
def get_ddb_table(table_name: str) -> Any:
    return get_dynamodb_resource().Table(table_name)
