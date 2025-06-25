#!/usr/bin/env python3
"""
Focused test for the AI selection functionality (ps-ai-selection).

This test covers:
1. Creating a stopped pulse in DynamoDB
2. Simulating DynamoDB stream event 
3. Testing AI selection logic with enhanced worthiness calculation
4. Verifying budget tracking and gamification features
5. Testing different worthiness scenarios (exceptional, good, low)

Uses moto for DynamoDB mocking and tests the enhanced AI selection algorithm.
"""

import sys
import os
import datetime
import json
from decimal import Decimal
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
        "PARAMETER_PREFIX": "/pulseshrine/ai/",
    }
)

backend_src = os.path.join(os.path.dirname(__file__), "../../src")
tests_path = os.path.join(backend_src, "../tests")
shared_path = os.path.join(backend_src, "shared/lambda_layer/python")
sys.path.insert(0, tests_path)
sys.path.insert(0, shared_path)

from fixtures.ddb import (
    create_stop_pulse_table,
    get_stop_pulse_table_name,
)

# Create SSM parameters for testing
def create_ssm_parameters():
    """Create the required SSM parameters for AI configuration."""
    import boto3
    
    ssm = boto3.client("ssm", region_name="us-east-1")
    
    # Create the required parameters with default values
    parameters = [
        {
            "Name": "/pulseshrine/ai/max_cost_per_pulse_cents",
            "Value": "2",
            "Type": "String",
            "Description": "Maximum cost per pulse for AI enhancement (cents)"
        },
        {
            "Name": "/pulseshrine/ai/enabled",
            "Value": "true",
            "Type": "String",
            "Description": "Whether AI enhancement is enabled"
        },
        {
            "Name": "/pulseshrine/ai/bedrock_model_id",
            "Value": "amazon.titan-text-express-v1",
            "Type": "String",
            "Description": "Bedrock model ID for AI enhancement"
        }
    ]
    
    for param in parameters:
        ssm.put_parameter(**param)

# Create AI usage tracking table fixture
def create_ai_usage_tracking_table():
    """Create the AI usage tracking table for testing."""
    import boto3
    from moto import mock_aws
    
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    
    table = dynamodb.create_table(
        TableName="ai-usage-tracking",
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "date", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "date", "AttributeType": "S"},
            {"AttributeName": "month", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "UserIdMonthIndex",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "month", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            }
        ],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    
    return table

stop_table_name = get_stop_pulse_table_name()
ai_usage_table_name = "ai-usage-tracking"

# Set environment variables for the handlers
os.environ.update(
    {
        "STOP_PULSE_TABLE_NAME": stop_table_name,
        "AI_USAGE_TRACKING_TABLE_NAME": ai_usage_table_name,
    }
)

# Add paths for importing backend code
ai_selection_handler_path = os.path.join(backend_src, "handlers/events/ai_selection")
sys.path.insert(0, ai_selection_handler_path)

# Import the AI selection handler
from ai_selection.app import handler as ai_selection_handler


def create_ddb_stream_event(pulse_data, event_name="INSERT"):
    """Create a DynamoDB stream event for testing."""
    # Convert Python values to DynamoDB format
    def to_ddb_format(value):
        if isinstance(value, str):
            return {"S": value}
        elif isinstance(value, (int, float)):
            return {"N": str(value)}
        elif isinstance(value, bool):
            return {"BOOL": value}
        elif isinstance(value, list):
            return {"L": [to_ddb_format(item) for item in value]}
        elif isinstance(value, dict):
            return {"M": {k: to_ddb_format(v) for k, v in value.items()}}
        elif value is None:
            return {"NULL": True}
        else:
            return {"S": str(value)}

    ddb_item = {k: to_ddb_format(v) for k, v in pulse_data.items()}

    event = {
        "Records": [
            {
                "eventID": "test-event-123",
                "eventName": event_name,
                "eventVersion": "1.1",
                "eventSource": "aws:dynamodb",
                "awsRegion": "us-east-1",
                "dynamodb": {
                    "ApproximateCreationDateTime": 1234567890.0,
                    "Keys": {
                        "pulse_id": {"S": pulse_data["pulse_id"]}
                    },
                    "NewImage": ddb_item if event_name == "INSERT" else None,
                    "SequenceNumber": "123456789",
                    "SizeBytes": 1000,
                    "StreamViewType": "NEW_IMAGE"
                },
                "eventSourceARN": f"arn:aws:dynamodb:us-east-1:123456789012:table/{stop_table_name}/stream/2023-01-01T00:00:00.000"
            }
        ]
    }
    
    return event


def create_test_pulse_data(worthiness_type="exceptional"):
    """Create test pulse data with different worthiness levels."""
    base_pulse = {
        "pulse_id": f"test-pulse-{worthiness_type}-123",
        "user_id": "test-user-ai-selection",
        "start_time": "2023-12-01T10:00:00Z",
        "stopped_at": "2023-12-01T12:30:00Z",
        "intent_emotion": "focused",
        "reflection_emotion": "accomplished",
        "tags": ["coding", "ai", "productivity"],
        "is_public": False,
        "timestamp": 1701432000,
        "inverted_timestamp": -1701432000,
    }
    
    if worthiness_type == "exceptional":
        # High worthiness: Long session, detailed content, breakthrough keywords
        base_pulse.update({
            "intent": "Implementing a revolutionary AI-powered productivity tracking system with advanced machine learning algorithms for intelligent task prioritization and breakthrough analytics dashboard",
            "reflection": "This was an absolutely groundbreaking session! I successfully developed a novel approach to AI-enhanced productivity tracking using cutting-edge neural networks and transformer models. The breakthrough came when I discovered a pioneering algorithm that can predict user productivity patterns with unprecedented accuracy. This innovative solution represents a paradigm shift in how we understand and optimize human productivity through artificial intelligence. The implementation involved sophisticated deep learning techniques, advanced data visualization, and revolutionary user experience design patterns.",
            "duration_seconds": 9000,  # 2.5 hours
        })
    elif worthiness_type == "good":
        # Medium worthiness: Decent session, moderate content
        base_pulse.update({
            "intent": "Working on improving the analytics dashboard with better data visualization and user interface enhancements",
            "reflection": "Great session! Made significant progress on the dashboard improvements. Added several new chart types and enhanced the user interface. The data visualization is much clearer now and users should find it more intuitive. Feeling productive and satisfied with the work completed.",
            "duration_seconds": 3600,  # 1 hour
        })
    elif worthiness_type == "low":
        # Low worthiness: Short session, minimal content
        base_pulse.update({
            "intent": "Quick fix",
            "reflection": "Fixed a small bug",
            "duration_seconds": 600,  # 10 minutes
        })
    
    return base_pulse


class MockContext:
    """Mock Lambda context for testing."""
    def __init__(self):
        self.aws_request_id = "test-request-ai-selection"
        self.log_group_name = "test-log-group"
        self.log_stream_name = "test-log-stream"
        self.function_name = "ps-ai-selection"
        self.memory_limit_in_mb = 1024
        self.function_version = "1"
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:ps-ai-selection"
        self.get_remaining_time_in_millis = lambda: 30000


@mock_aws
def test_ai_selection_exceptional_worthiness():
    """Test AI selection with exceptional worthiness content."""
    print("🧠 Testing AI selection with EXCEPTIONAL worthiness content")
    print("=" * 70)
    
    # Setup AWS services
    create_ssm_parameters()  # Create SSM parameters to avoid warnings
    stop_table = create_stop_pulse_table()
    ai_usage_table = create_ai_usage_tracking_table()
    
    # Create exceptional worthiness test data
    pulse_data = create_test_pulse_data("exceptional")
    event = create_ddb_stream_event(pulse_data)
    context = MockContext()
    
    print(f"📝 Test pulse data:")
    print(f"   Intent: {pulse_data['intent'][:80]}...")
    print(f"   Reflection: {pulse_data['reflection'][:80]}...")
    print(f"   Duration: {pulse_data['duration_seconds']} seconds ({pulse_data['duration_seconds']/3600:.1f} hours)")
    print(f"   User ID: {pulse_data['user_id']}")
    
    # Test AI selection
    print(f"\n⚡ Running AI selection handler...")
    result = ai_selection_handler(event, context)
    
    print(f"✅ AI selection completed!")
    print(f"   AI Worthy: {result.get('aiWorthy')}")
    print(f"   Decision Reason: {result.get('selectionInfo', {}).get('decision_reason')}")
    print(f"   Worthiness Score: {result.get('selectionInfo', {}).get('worthiness_score', 0):.3f}")
    print(f"   Estimated Cost: {result.get('selectionInfo', {}).get('estimated_cost_cents')} cents")
    
    # Verify exceptional content is selected for AI enhancement
    assert result.get('aiWorthy') == True, "Exceptional content should be AI worthy"
    assert result.get('selectionInfo', {}).get('worthiness_score', 0) >= 0.8, "Exceptional content should have high worthiness score"
    assert "Exceptional worthiness" in result.get('selectionInfo', {}).get('decision_reason', ''), "Should indicate exceptional worthiness"
    
    print(f"✅ Exceptional worthiness test passed!")
    return result


@mock_aws 
def test_ai_selection_good_worthiness():
    """Test AI selection with good worthiness content."""
    print("\n🧠 Testing AI selection with GOOD worthiness content")
    print("=" * 70)
    
    # Setup AWS services
    create_ssm_parameters()  # Create SSM parameters to avoid warnings
    stop_table = create_stop_pulse_table()
    ai_usage_table = create_ai_usage_tracking_table()
    
    # Create good worthiness test data
    pulse_data = create_test_pulse_data("good")
    event = create_ddb_stream_event(pulse_data)
    context = MockContext()
    
    print(f"📝 Test pulse data:")
    print(f"   Intent: {pulse_data['intent']}")
    print(f"   Reflection: {pulse_data['reflection'][:80]}...")
    print(f"   Duration: {pulse_data['duration_seconds']} seconds ({pulse_data['duration_seconds']/3600:.1f} hours)")
    
    # Test AI selection multiple times since it's probabilistic for good content
    ai_worthy_count = 0
    total_tests = 10
    
    print(f"\n⚡ Running AI selection handler {total_tests} times (probabilistic for good content)...")
    
    for i in range(total_tests):
        result = ai_selection_handler(event, context)
        if result.get('aiWorthy'):
            ai_worthy_count += 1
    
    worthiness_score = result.get('selectionInfo', {}).get('worthiness_score', 0)
    print(f"✅ Good worthiness test completed!")
    print(f"   Worthiness Score: {worthiness_score:.3f}")
    print(f"   AI Worthy Rate: {ai_worthy_count}/{total_tests} ({ai_worthy_count/total_tests*100:.1f}%)")
    print(f"   Decision Reason: {result.get('selectionInfo', {}).get('decision_reason')}")
    
    # Verify good content has reasonable worthiness and some probability of AI enhancement
    assert worthiness_score >= 0.4, "Good content should have decent worthiness score"
    assert worthiness_score < 0.8, "Good content should not reach exceptional threshold"
    assert "Good worthiness" in result.get('selectionInfo', {}).get('decision_reason', '') or ai_worthy_count > 0, "Should indicate good worthiness or have some AI selections"
    
    print(f"✅ Good worthiness test passed!")
    return result


@mock_aws
def test_ai_selection_low_worthiness():
    """Test AI selection with low worthiness content."""
    print("\n🧠 Testing AI selection with LOW worthiness content")
    print("=" * 70)
    
    # Setup AWS services
    create_ssm_parameters()  # Create SSM parameters to avoid warnings
    stop_table = create_stop_pulse_table()
    ai_usage_table = create_ai_usage_tracking_table()
    
    # Create low worthiness test data
    pulse_data = create_test_pulse_data("low")
    event = create_ddb_stream_event(pulse_data)
    context = MockContext()
    
    print(f"📝 Test pulse data:")
    print(f"   Intent: {pulse_data['intent']}")
    print(f"   Reflection: {pulse_data['reflection']}")
    print(f"   Duration: {pulse_data['duration_seconds']} seconds ({pulse_data['duration_seconds']/60:.1f} minutes)")
    
    # Test AI selection
    print(f"\n⚡ Running AI selection handler...")
    result = ai_selection_handler(event, context)
    
    print(f"✅ AI selection completed!")
    print(f"   AI Worthy: {result.get('aiWorthy')}")
    print(f"   Decision Reason: {result.get('selectionInfo', {}).get('decision_reason')}")
    print(f"   Worthiness Score: {result.get('selectionInfo', {}).get('worthiness_score', 0):.3f}")
    print(f"   Estimated Cost: {result.get('selectionInfo', {}).get('estimated_cost_cents')} cents")
    
    # Verify low content is not selected for AI enhancement
    worthiness_score = result.get('selectionInfo', {}).get('worthiness_score', 0)
    assert result.get('aiWorthy') == False, "Low worthiness content should not be AI worthy"
    assert worthiness_score < 0.4, "Low worthiness content should have low score"
    assert "Low worthiness" in result.get('selectionInfo', {}).get('decision_reason', ''), "Should indicate low worthiness"
    
    print(f"✅ Low worthiness test passed!")
    return result


@mock_aws
def test_ai_selection_budget_limitation():
    """Test AI selection with budget limitations."""
    print("\n💰 Testing AI selection with BUDGET limitations")
    print("=" * 70)
    
    # Setup AWS services
    create_ssm_parameters()  # Create SSM parameters to avoid warnings
    stop_table = create_stop_pulse_table()
    ai_usage_table = create_ai_usage_tracking_table()
    
    # Create a user with exhausted budget
    import boto3
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(ai_usage_table_name)
    
    user_id = "test-user-budget-exhausted"
    today = datetime.date.today().strftime("%Y-%m-%d")
    month = datetime.date.today().strftime("%Y-%m")
    
    # Create a budget record showing user has exhausted their monthly budget
    table.put_item(Item={
        "user_id": user_id,
        "date": today,
        "daily_cost_cents": 0,
        "daily_ai_credits": 0,  # No credits left
        "daily_pulses_enhanced": 5,
        "monthly_cost_cents": 50,  # Reached free tier monthly cap
        "monthly_ai_credits": 0,
        "user_tier": "free",
        "streak_days": 3,
        "achievements": [],
        "last_gift_date": "",
        "total_ai_enhancements": 5,
        "month": month,
        "ttl": int((datetime.datetime.now() + datetime.timedelta(days=90)).timestamp())
    })
    
    # Create exceptional worthiness test data but with exhausted budget user
    pulse_data = create_test_pulse_data("exceptional")
    pulse_data["user_id"] = user_id
    event = create_ddb_stream_event(pulse_data)
    context = MockContext()
    
    print(f"📝 Test setup:")
    print(f"   User ID: {user_id}")
    print(f"   Monthly Budget Used: 50 cents (at free tier limit)")
    print(f"   AI Credits: 0")
    print(f"   Content: Exceptional worthiness")
    
    # Test AI selection
    print(f"\n⚡ Running AI selection handler...")
    result = ai_selection_handler(event, context)
    
    print(f"✅ AI selection completed!")
    print(f"   AI Worthy: {result.get('aiWorthy')}")
    print(f"   Decision Reason: {result.get('selectionInfo', {}).get('decision_reason')}")
    print(f"   Worthiness Score: {result.get('selectionInfo', {}).get('worthiness_score', 0):.3f}")
    
    # Verify budget limitation prevents AI enhancement even for exceptional content
    assert result.get('aiWorthy') == False, "Should not be AI worthy due to budget limitation"
    assert result.get('selectionInfo', {}).get('worthiness_score', 0) >= 0.8, "Should still have high worthiness score"
    decision_reason = result.get('selectionInfo', {}).get('decision_reason', '')
    assert "budget" in decision_reason.lower() or "monthly" in decision_reason.lower(), "Should indicate budget limitation"
    
    print(f"✅ Budget limitation test passed!")
    return result


@mock_aws
def test_ai_selection_data_structure():
    """Test AI selection output data structure."""
    print("\n📋 Testing AI selection OUTPUT data structure")
    print("=" * 70)
    
    # Setup AWS services
    create_ssm_parameters()  # Create SSM parameters to avoid warnings
    stop_table = create_stop_pulse_table()
    ai_usage_table = create_ai_usage_tracking_table()
    
    # Create test data
    pulse_data = create_test_pulse_data("exceptional")
    event = create_ddb_stream_event(pulse_data)
    context = MockContext()
    
    # Test AI selection
    print(f"⚡ Running AI selection handler...")
    result = ai_selection_handler(event, context)
    
    print(f"✅ Validating output structure...")
    
    # Verify required fields in result
    required_fields = ['aiWorthy', 'aiConfig', 'pulseData', 'originalEvent', 'selectionInfo', 'recordInfo']
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"
        print(f"   ✓ {field}: present")
    
    # Verify selectionInfo structure
    selection_info = result.get('selectionInfo', {})
    selection_required = ['decision_reason', 'worthiness_score', 'estimated_cost_cents']
    for field in selection_required:
        assert field in selection_info, f"Missing selectionInfo field: {field}"
        print(f"   ✓ selectionInfo.{field}: present")
    
    # Verify recordInfo structure
    record_info = result.get('recordInfo', {})
    record_required = ['eventId', 'eventName', 'pulseId', 'userId']
    for field in record_required:
        assert field in record_info, f"Missing recordInfo field: {field}"
        print(f"   ✓ recordInfo.{field}: present")
    
    # Verify data types
    assert isinstance(result['aiWorthy'], bool), "aiWorthy should be boolean"
    assert isinstance(selection_info['worthiness_score'], (int, float)), "worthiness_score should be numeric"
    assert isinstance(selection_info['estimated_cost_cents'], (int, float)), "estimated_cost_cents should be numeric"
    
    print(f"✅ Data structure validation passed!")
    print(f"   Sample output structure:")
    print(f"   - aiWorthy: {result['aiWorthy']}")
    print(f"   - selectionInfo.worthiness_score: {selection_info['worthiness_score']:.3f}")
    print(f"   - selectionInfo.estimated_cost_cents: {selection_info['estimated_cost_cents']}")
    print(f"   - recordInfo.pulseId: {record_info['pulseId']}")
    
    return result


def main():
    """Run all AI selection tests."""
    print("🧪 PulseShrine AI Selection (ps-ai-selection) Test Suite")
    print("Testing enhanced AI selection with value-first budget approach")
    print("=" * 80)
    
    try:
        # Test different worthiness scenarios
        exceptional_result = test_ai_selection_exceptional_worthiness()
        good_result = test_ai_selection_good_worthiness() 
        low_result = test_ai_selection_low_worthiness()
        budget_result = test_ai_selection_budget_limitation()
        structure_result = test_ai_selection_data_structure()
        
        print(f"\n🏆 ALL AI SELECTION TESTS PASSED!")
        print("=" * 80)
        print("✅ Exceptional worthiness → AI worthy (guaranteed)")
        print("✅ Good worthiness → AI worthy (probabilistic)")
        print("✅ Low worthiness → Not AI worthy")
        print("✅ Budget limitation → Blocks AI enhancement")
        print("✅ Output data structure → Valid and complete")
        print("\n🎯 Enhanced AI selection algorithm working correctly!")
        print("   - Value-first approach prioritizes quality content")
        print("   - Budget constraints properly enforced")
        print("   - Worthiness calculation considers investment and engagement")
        print("   - Gamification and reward system integrated")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ AI SELECTION TESTS FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)