import boto3
from moto import mock_aws
from datetime import datetime

# Your pulse creation code here (from previous artifact)
from src.shared.services.aws import get_region_name
from src.shared.services.pulse import start_pulse, get_start_pulse, get_start_pulse_table_name


@mock_aws
def test_create_pulse_with_moto():
    """Test pulse creation using moto mock"""
    # Create mock DynamoDB
    dynamodb = boto3.resource("dynamodb", region_name=get_region_name())

    # Create test table
    table = dynamodb.create_table(
        TableName=get_start_pulse_table_name(),
        KeySchema=[{"AttributeName": "pulse_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "pulse_id", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "start_time", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "user_id-start_time-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "start_time", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Test pulse creation
    pulse_id = start_pulse(
        user_id="test_user",
        start_time=datetime.now(),
        intent="test_intent",
        duration_seconds=300,
        tags=["test", "example"],
        is_public=True,
        table_name=get_start_pulse_table_name(),
    )

    assert pulse_id is not None
    assert len(pulse_id) == 36  # UUID length

    # Verify the pulse was created
    pulse = get_start_pulse(
        pulse_id=pulse_id,
        table_name=get_start_pulse_table_name(),
    )
    assert pulse["user_id"] == "test_user"
    assert pulse["intent"] == "test_intent"

    pulse_id = start_pulse(
        user_id="test_user_2",
        start_time=datetime.now(),
        intent="other_intent",
        table_name=get_start_pulse_table_name()
    )
    pulse = get_start_pulse(
        pulse_id=pulse_id,
        table_name=get_start_pulse_table_name(),
    )
    assert pulse["user_id"] == "test_user_2"
    assert pulse["intent"] == "other_intent"
