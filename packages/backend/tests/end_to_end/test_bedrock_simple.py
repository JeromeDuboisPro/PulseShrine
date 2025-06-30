#!/usr/bin/env python3
"""
Simple Bedrock enhancement test.

This test covers:
- Bedrock enhancement (Event handler) → AI-powered title/badge/insights generation

Uses real AWS Bedrock service via AWS_PROFILE credentials.
"""

import sys
import os
import datetime

# Set AWS environment variables for testing
# Note: AWS_PROFILE should be set externally to use real credentials for Bedrock
# os.environ.update(
#     {
#         "AWS_DEFAULT_REGION": "us-east-1",
#         "AWS_REGION": "us-east-1",
#         "PARAMETER_PREFIX": "/pulseshrine/ai/",
#     }
# )

backend_src = os.path.join(os.path.dirname(__file__), "../../src")
shared_path = os.path.join(backend_src, "shared/lambda_layer/python")
bedrock_enhancement_path = os.path.join(
    backend_src, "handlers/events/bedrock_enhancement"
)

sys.path.insert(0, shared_path)
sys.path.insert(0, bedrock_enhancement_path)

# Import the real backend code
from shared.models.pulse import StopPulse
from bedrock_enhancement.app import handler as bedrock_enhancement_handler


def test_bedrock_enhancement():
    """Test Bedrock enhancement with real AWS calls."""

    print("🚀 Testing PulseShrine Bedrock enhancement")
    print("=" * 60)
    print("⚠️  NOTE: This test uses REAL AWS Bedrock service calls!")
    print("   Make sure AWS_PROFILE is set with valid credentials and Bedrock access.")
    print("   This test will incur actual AWS costs.")
    print("=" * 60)

    # Check if AWS_PROFILE is set
    if not os.environ.get("AWS_PROFILE"):
        print("❌ AWS_PROFILE environment variable not set!")
        print("   Please set AWS_PROFILE=your-profile-name before running this test")
        raise EnvironmentError("AWS_PROFILE not set")

    print(f"✅ Using AWS Profile: {os.environ.get('AWS_PROFILE')}")

    # Create test pulse data - substantial content to trigger good AI response
    start_time = datetime.datetime.now(datetime.timezone.utc)
    stop_time = start_time + datetime.timedelta(hours=2)

    stop_pulse = StopPulse(
        user_id="test-user-bedrock-456",
        pulse_id="test-pulse-123",
        start_time=start_time.isoformat(),
        intent="Revolutionary deep learning research session: implementing novel transformer architecture for multimodal AI reasoning with breakthrough attention mechanisms",
        duration_seconds=7200,  # 2 hours - substantial session
        intent_emotion="innovative",
        tags=["research", "deep-learning", "ai", "breakthrough", "innovation"],
        is_public=True,
        reflection="Incredible breakthrough session! Successfully designed and implemented a novel transformer architecture that combines visual and textual reasoning in ways never seen before. The attention mechanisms I developed show 40% improvement over existing models. This could revolutionize how AI systems understand multimodal content. Feeling absolutely exhilarated by this research achievement!",
        stopped_at=stop_time.isoformat(),
        reflection_emotion="breakthrough",
    )

    print(f"\n📝 Test pulse data prepared:")
    print(f"   User ID: {stop_pulse.user_id}")
    print(f"   Intent: {stop_pulse.intent[:80]}...")
    print(
        f"   Duration: {stop_pulse.duration_seconds} seconds ({stop_pulse.duration_seconds/3600:.1f} hours)"
    )
    print(f"   Intent Emotion: {stop_pulse.intent_emotion}")
    print(f"   Reflection Emotion: {stop_pulse.reflection_emotion}")
    print(f"   Reflection length: {len(stop_pulse.reflection)} chars")

    try:
        # Create event structure for Bedrock enhancement
        print(f"\n⚡ Calling Bedrock enhancement handler...")
        print("⚠️  Making REAL AWS Bedrock API calls - this will incur costs!")
        print(f"   Using AWS Profile: {os.environ.get('AWS_PROFILE')}")

        bedrock_event = {
            "pulseData": stop_pulse.model_dump(),
            "stopPulse": stop_pulse.model_dump(),
            "aiSelected": True,
            "aiScore": 0.9,
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

        # This will make real AWS Bedrock API calls using AWS_PROFILE credentials
        bedrock_result = bedrock_enhancement_handler(bedrock_event, context)

        print(f"✅ Bedrock enhancement completed successfully!")
        print(f"\n🎯 RESULTS:")
        print(f"   Enhanced: {bedrock_result.get('enhanced', 'N/A')}")
        print(
            f"   Enhanced Title: '{bedrock_result.get('enhancedPulse', {}).get('gen_title', 'N/A')}'"
        )
        print(
            f"   Enhanced Badge: '{bedrock_result.get('enhancedPulse', {}).get('gen_badge', 'N/A')}'"
        )

        ai_insights = bedrock_result.get("enhancedPulse", {}).get("ai_insights", {})
        if ai_insights:
            print(f"   AI Insights:")
            print(
                f"     Productivity Score: {ai_insights.get('productivity_score', 'N/A')}"
            )
            print(f"     Key Insight: '{ai_insights.get('key_insight', 'N/A')}'")
            print(
                f"     Next Suggestion: '{ai_insights.get('next_suggestion', 'N/A')}'"
            )
            print(
                f"     Mood Assessment: '{ai_insights.get('mood_assessment', 'N/A')}'"
            )
            print(
                f"     Emotion Pattern: '{ai_insights.get('emotion_pattern', 'N/A')}'"
            )

        print(f"   AI Cost: ${bedrock_result.get('aiCost', 0)/100:.4f}")

        # Basic validation
        assert (
            bedrock_result.get("enhanced") == True
        ), "Enhancement should be marked as successful"
        enhanced_pulse = bedrock_result.get("enhancedPulse", {})
        assert (
            len(enhanced_pulse.get("gen_title", "")) > 0
        ), "AI title should not be empty"
        assert (
            len(enhanced_pulse.get("gen_badge", "")) > 0
        ), "AI badge should not be empty"
        assert bedrock_result.get("aiCost", 0) > 0, "AI cost should be tracked"

        print(f"\n✅ Validation passed!")
        print(f"🎉 Bedrock enhancement test completed successfully!")

        return {
            "success": True,
            "generated_title": enhanced_pulse.get("gen_title"),
            "generated_badge": enhanced_pulse.get("gen_badge"),
            "ai_insights": ai_insights,
            "ai_cost": bedrock_result.get("aiCost", 0),
        }

    except Exception as e:
        print(f"❌ Bedrock enhancement test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def main():
    """Run the Bedrock enhancement test."""

    print("🧪 PulseShrine Bedrock Enhancement Test")
    print("Testing REAL AWS Bedrock AI enhancement")
    print("⚠️  WARNING: This test uses real AWS Bedrock and incurs costs!")
    print("=" * 60)

    try:
        result = test_bedrock_enhancement()

        if result["success"]:
            print(f"\n🏆 ALL TESTS PASSED!")
            print(f"AI-Enhanced Title: '{result['generated_title']}'")
            print(f"AI-Enhanced Badge: '{result['generated_badge']}'")
            print(f"AI Cost: ${result['ai_cost']/100:.4f}")
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
