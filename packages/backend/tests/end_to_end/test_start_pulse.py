#!/usr/bin/env python3
"""
End-to-end test for start_pulse functionality using real backend code and moto for DynamoDB mocking.

This test imports the actual start_pulse service function and validates it works with a mocked DynamoDB table.
"""

import sys
import os
import boto3
from moto import mock_aws

# Set AWS environment variables for testing
os.environ.update(
    {
        "AWS_DEFAULT_REGION": "us-east-1",
        "AWS_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SECURITY_TOKEN": "testing",
        "AWS_SESSION_TOKEN": "testing",
    }
)

# Add paths for importing backend code
backend_src = os.path.join(os.path.dirname(__file__), "../../src")
shared_path = os.path.join(backend_src, "shared/lambda_layer/python")
start_pulse_handler_path = os.path.join(backend_src, "handlers/api/start_pulse")

sys.path.insert(0, shared_path)
sys.path.insert(0, start_pulse_handler_path)

# Import the real backend code
from shared.models.pulse import StartPulse

# Import start_pulse service function directly
from start_pulse.services import start_pulse


def setup_dynamodb_table():
    """Create a local DynamoDB table using moto."""
    table_name = "test-start-pulse-table"

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create table
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "pulse_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "pulse_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # Wait for table to be created
    table.meta.client.get_waiter("table_exists").wait(TableName=table_name)

    return table_name


@mock_aws
def test_start_pulse_integration():
    """Test the start_pulse function with real backend code and mocked DynamoDB."""

    print("🚀 Testing start_pulse integration with real backend code")
    print("=" * 60)

    # Test data
    pulse_data = StartPulse(
        user_id="test-user-123",
        intent="Focus deeply on testing the backend integration",
        duration_seconds=1800,  # 30 minutes
        intent_emotion="focused",
        tags=["testing", "integration"],
        is_public=False,
    )

    print(f"📝 Test data prepared:")
    print(f"   User ID: {pulse_data.user_id}")
    print(f"   Intent: {pulse_data.intent}")
    print(f"   Duration: {pulse_data.duration_seconds} seconds")
    print(f"   Emotion: {pulse_data.intent_emotion}")
    print(f"   Tags: {pulse_data.tags}")
    print(f"   Is Public: {pulse_data.is_public}")

    # Setup mocked DynamoDB table
    table_name = setup_dynamodb_table()
    print(f"\n🗄️  Created local DynamoDB table: {table_name}")

    try:
        # Call the real start_pulse function
        print(f"\n⚡ Calling real start_pulse function...")
        result = start_pulse(pulse_data=pulse_data, table_name=table_name)

        print(f"✅ start_pulse executed successfully!")
        print(f"   Generated Pulse ID: {result.pulse_id}")
        print(f"   Start Time: {result.start_time_dt.isoformat()}")
        print(f"   User ID: {result.user_id}")
        print(f"   Intent: {result.intent}")

        # Verify the data was stored in DynamoDB
        print(f"\n🔍 Verifying data in DynamoDB...")
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.Table(table_name)

        response = table.get_item(Key={"pulse_id": result.pulse_id})

        if "Item" in response:
            item = response["Item"]
            print(f"✅ Data found in DynamoDB:")
            print(f"   Pulse ID: {item['pulse_id']}")
            print(f"   User ID: {item['user_id']}")
            print(f"   Intent: {item['intent']}")
            print(f"   Start Time: {item['start_time']}")
            print(f"   Duration: {item.get('duration_seconds', 'N/A')} seconds")
            print(f"   Intent Emotion: {item.get('intent_emotion', 'N/A')}")
            print(f"   Tags: {item.get('tags', 'N/A')}")
            print(f"   Is Public: {item['is_public']}")
            print(f"   Created At: {item['created_at']}")

            # Validate data integrity
            assert item["user_id"] == pulse_data.user_id
            assert item["intent"] == pulse_data.intent
            assert item["is_public"] == pulse_data.is_public
            assert str(item["duration_seconds"]) == str(pulse_data.duration_seconds)
            assert item["intent_emotion"] == pulse_data.intent_emotion
            assert item["tags"] == pulse_data.tags

            print(f"\n✅ Data integrity validation passed!")

        else:
            raise Exception("Data not found in DynamoDB")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

    print(f"\n🎉 Integration test completed successfully!")
    print("=" * 60)
    print("✅ Real backend code executed")
    print("✅ DynamoDB table created and populated")
    print("✅ Data integrity validated")
    print("✅ Ready for production deployment")

    return True


def main():
    """Run the integration test with mocked AWS services."""

    print("🧪 PulseShrine Start Pulse Integration Test")
    print("Using real backend code with mocked DynamoDB")
    print("=" * 60)

    try:
        success = test_start_pulse_integration()

        if success:
            print(f"\n🏆 ALL TESTS PASSED!")
            return 0
        else:
            print(f"\n❌ TESTS FAILED!")
            return 1

    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
