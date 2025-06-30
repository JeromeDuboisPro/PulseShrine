#!/usr/bin/env python3
"""
End-to-end test for the complete PulseShrine pipeline using standard enhancement.

This test covers:
1. Start pulse (API) → DynamoDB
2. Stop pulse (API) → DynamoDB
3. Standard enhancement (Event handler) → Title/badge generation
4. Pure ingest (Event handler) → Final storage in ingested table
5. Verification using get_* API handlers

Uses moto for DynamoDB mocking, DDB fixtures, and real backend code.
"""

import sys
import os
import datetime
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
    create_start_pulse_table,
    create_stop_pulse_table,
    create_ingested_pulse_table,
    get_start_pulse_table_name,
    get_stop_pulse_table_name,
    get_ingested_pulse_table_name,
)

start_table_name = get_start_pulse_table_name()
stop_table_name = get_stop_pulse_table_name()
ingested_table_name = get_ingested_pulse_table_name()

# Set environment variables for the handlers
os.environ.update(
    {
        "START_PULSE_TABLE_NAME": start_table_name,
        "STOP_PULSE_TABLE_NAME": stop_table_name,
        "INGESTED_PULSE_TABLE_NAME": ingested_table_name,
    }
)

# Add paths for importing backend code


start_pulse_handler_path = os.path.join(backend_src, "handlers/api/start_pulse")
stop_pulse_handler_path = os.path.join(backend_src, "handlers/api/stop_pulse")
get_start_pulse_handler_path = os.path.join(backend_src, "handlers/api/get_start_pulse")
get_stop_pulse_handler_path = os.path.join(backend_src, "handlers/api/get_stop_pulse")
get_ingested_pulse_handler_path = os.path.join(
    backend_src, "handlers/api/get_ingested_pulse"
)
standard_enhancement_path = os.path.join(
    backend_src, "handlers/events/standard_enhancement"
)
pure_ingest_path = os.path.join(backend_src, "handlers/events/pure_ingest")


sys.path.insert(0, start_pulse_handler_path)
sys.path.insert(0, stop_pulse_handler_path)
sys.path.insert(0, get_start_pulse_handler_path)
sys.path.insert(0, get_stop_pulse_handler_path)
sys.path.insert(0, get_ingested_pulse_handler_path)
sys.path.insert(0, standard_enhancement_path)
sys.path.insert(0, pure_ingest_path)


# Import the real backend code
from shared.models.pulse import StartPulse, StopPulse, ArchivedPulse
from start_pulse.services import start_pulse
from stop_pulse.services import stop_pulse
from get_start_pulse.services import get_start_pulse
from get_stop_pulse.services import get_stop_pulses
from get_ingested_pulse.services import get_ingested_pulses
from standard_enhancement.app import handler as standard_enhancement_handler
from pure_ingest.app import handler as pure_ingest_handler


def convert_ddb_to_stop_pulse(pulse_data):
    """Convert DynamoDB item format to StopPulse model."""
    return StopPulse(
        user_id=pulse_data["user_id"],
        pulse_id=pulse_data["pulse_id"],
        start_time=pulse_data["start_time"],
        intent=pulse_data["intent"],
        reflection=pulse_data["reflection"],
        reflection_emotion=pulse_data.get("reflection_emotion"),
        stopped_at=pulse_data["stopped_at"],
        duration_seconds=int(pulse_data.get("duration_seconds", 0)),
        intent_emotion=pulse_data.get("intent_emotion"),
        tags=pulse_data.get("tags", []),
        is_public=pulse_data.get("is_public", False),
    )


@mock_aws
def test_end_to_end_standard_pipeline():
    """Test the complete standard enhancement pipeline."""

    print("🚀 Testing complete PulseShrine pipeline with standard enhancement")
    print("=" * 80)

    # Setup mocked DynamoDB tables using fixtures
    print(f"🗄️  Creating DynamoDB tables using fixtures...")
    start_table = create_start_pulse_table()
    stop_table = create_stop_pulse_table()
    ingested_table = create_ingested_pulse_table()

    print(f"✅ Created DynamoDB tables:")
    print(f"   Start: {start_table_name}")
    print(f"   Stop: {stop_table_name}")
    print(f"   Ingested: {ingested_table_name}")

    # Test data
    user_id = "test-user-pipeline-123"
    start_time = datetime.datetime.now(datetime.timezone.utc)
    stop_time = start_time + datetime.timedelta(minutes=45)

    pulse_data = StartPulse(
        user_id=user_id,
        intent="Deep work session on implementing the PulseShrine analytics dashboard",
        duration_seconds=2700,  # 45 minutes
        intent_emotion="focused",
        tags=["coding", "analytics", "deep-work"],
        is_public=True,
    )

    print(f"\n📝 Test data prepared:")
    print(f"   User ID: {pulse_data.user_id}")
    print(f"   Intent: {pulse_data.intent}")
    print(
        f"   Duration: {pulse_data.duration_seconds} seconds ({pulse_data.duration_seconds/60:.1f} minutes)"
    )
    print(f"   Emotion: {pulse_data.intent_emotion}")
    print(f"   Tags: {pulse_data.tags}")
    print(f"   Is Public: {pulse_data.is_public}")

    try:
        # STEP 1: Start pulse
        print(f"\n⚡ STEP 1: Starting pulse...")
        start_result = start_pulse(pulse_data=pulse_data, table_name=start_table_name)
        print(f"✅ Pulse started successfully!")
        print(f"   Generated Pulse ID: {start_result.pulse_id}")
        print(f"   Start Time: {start_result.start_time_dt.isoformat()}")

        # Verify start pulse was stored using get_start_pulse API
        print(f"\n🔍 Verifying start pulse via API...")
        retrieved_start_pulse = get_start_pulse(
            user_id=user_id, table_name=start_table_name
        )
        assert retrieved_start_pulse is not None
        assert retrieved_start_pulse.pulse_id == start_result.pulse_id
        print(f"✅ Start pulse verified via get_start_pulse API")

        # STEP 2: Stop pulse
        print(f"\n⚡ STEP 2: Stopping pulse...")
        stop_result = stop_pulse(
            user_id=user_id,
            start_pulse_table_name=start_table_name,
            stop_pulse_table_name=stop_table_name,
            reflection="Amazing session! Built the entire analytics component with real-time charts and data visualization. Feeling super productive and energized.",
            stopped_at=stop_time,
            reflection_emotion="accomplished",
        )
        print(f"✅ Pulse stopped successfully!")
        print(f"   Pulse ID: {stop_result.pulse_id}")
        print(f"   Reflection: {stop_result.reflection}")
        print(f"   Reflection Emotion: {stop_result.reflection_emotion}")
        print(f"   Actual Duration: {stop_result.actual_duration_seconds} seconds")

        # Verify stop pulse was stored using get_stop_pulses API
        print(f"\n🔍 Verifying stop pulse via API...")
        retrieved_stop_pulses = get_stop_pulses(
            user_id=user_id, table_name=stop_table_name
        )
        assert len(retrieved_stop_pulses) == 1
        assert retrieved_stop_pulses[0].pulse_id == stop_result.pulse_id
        print(f"✅ Stop pulse verified via get_stop_pulses API")

        # STEP 3: Standard enhancement
        print(f"\n⚡ STEP 3: Applying standard enhancement...")

        # Create event structure for standard enhancement
        enhancement_event = {
            "pulseData": stop_result.model_dump(),
            "stopPulse": stop_result.model_dump(),
            "aiEnhanced": False,
        }

        # Mock lambda context
        class MockContext:
            def __init__(self):
                self.aws_request_id = "test-request-123"
                self.log_group_name = "test-log-group"
                self.log_stream_name = "test-log-stream"
                self.function_name = "test-function"
                self.memory_limit_in_mb = 1024
                self.function_version = "1"
                self.invoked_function_arn = (
                    "arn:aws:lambda:us-east-1:123456789012:function:test"
                )
                self.get_remaining_time_in_millis = lambda: 30000

        context = MockContext()

        enhancement_result = standard_enhancement_handler(enhancement_event, context)
        print(f"✅ Standard enhancement completed!")
        print(f"   Generated Title: '{enhancement_result.get('generatedTitle')}'")
        print(f"   Generated Badge: '{enhancement_result.get('generatedBadge')}'")
        print(f"   AI Enhanced: {enhancement_result.get('aiEnhanced', False)}")

        # STEP 4: Pure ingest
        print(f"\n⚡ STEP 4: Ingesting enhanced pulse...")

        ingest_result = pure_ingest_handler(enhancement_result, context)
        print(f"✅ Pulse ingested successfully!")
        print(f"   Success: {ingest_result.get('success')}")
        print(
            f"   Archived Pulse ID: {ingest_result.get('archivedPulse', {}).get('pulse_id')}"
        )

        # STEP 5: Verify final result using get_ingested_pulses API
        print(f"\n🔍 STEP 5: Verifying ingested data via API...")
        retrieved_ingested_pulses = get_ingested_pulses(
            user_id=user_id, table_name=ingested_table_name
        )

        if retrieved_ingested_pulses:
            ingested_pulse = retrieved_ingested_pulses[0]
            print(f"✅ Ingested pulse found via get_ingested_pulses API:")
            print(f"   Pulse ID: {ingested_pulse.pulse_id}")
            print(f"   User ID: {ingested_pulse.user_id}")
            print(f"   Generated Title: '{ingested_pulse.gen_title}'")
            print(f"   Generated Badge: '{ingested_pulse.gen_badge}'")
            print(f"   Intent: {ingested_pulse.intent}")
            print(f"   Reflection: {ingested_pulse.reflection}")
            print(f"   Duration: {ingested_pulse.duration_seconds} seconds")
            print(f"   Tags: {ingested_pulse.tags}")
            print(f"   Archived At: {ingested_pulse.archived_at}")

            # Data integrity validation
            assert ingested_pulse.user_id == user_id
            assert ingested_pulse.pulse_id == start_result.pulse_id
            assert ingested_pulse.intent == pulse_data.intent
            assert (
                ingested_pulse.reflection
                == "Amazing session! Built the entire analytics component with real-time charts and data visualization. Feeling super productive and energized."
            )
            assert ingested_pulse.gen_title == enhancement_result.get("generatedTitle")
            assert ingested_pulse.gen_badge == enhancement_result.get("generatedBadge")

            print(f"\n✅ Data integrity validation passed!")
        else:
            raise Exception("Ingested pulse not found via get_ingested_pulses API")

        print(f"\n🎉 End-to-end standard pipeline test completed successfully!")
        print("=" * 80)
        print("✅ Start pulse → DynamoDB → Verified via get_start_pulse API")
        print("✅ Stop pulse → DynamoDB → Verified via get_stop_pulses API")
        print("✅ Standard enhancement → Title/badge generation")
        print("✅ Pure ingest → Final storage → Verified via get_ingested_pulses API")
        print("✅ Complete pipeline functional with API verification!")

        return {
            "success": True,
            "pulse_id": start_result.pulse_id,
            "generated_title": enhancement_result.get("generatedTitle"),
            "generated_badge": enhancement_result.get("generatedBadge"),
            "ai_enhanced": False,
            "duration_seconds": stop_result.actual_duration_seconds,
            "final_pulse": ingested_pulse,
        }

    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def main():
    """Run the end-to-end standard pipeline test."""

    print("🧪 PulseShrine End-to-End Standard Pipeline Test")
    print("Testing complete flow with standard enhancement and API verification")
    print("=" * 80)

    try:
        result = test_end_to_end_standard_pipeline()

        if result["success"]:
            print(f"\n🏆 ALL TESTS PASSED!")
            print(f"Generated Title: '{result['generated_title']}'")
            print(f"Generated Badge: '{result['generated_badge']}'")
            print(f"Duration: {result['duration_seconds']} seconds")
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
