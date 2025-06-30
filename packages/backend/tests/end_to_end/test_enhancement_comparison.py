#!/usr/bin/env python3
"""
Enhancement Comparison Test: Standard vs Bedrock

This test compares the output quality between standard rule-based enhancement
and Bedrock AI enhancement using the exact same pulse input data.

Shows the clear value differentiation between the two approaches.
"""

import sys
import os
import datetime

# Set AWS environment variables for testing
os.environ.update(
    {
        "PARAMETER_PREFIX": "/pulseshrine/ai/",
    }
)

backend_src = os.path.join(os.path.dirname(__file__), "../../src")
shared_path = os.path.join(backend_src, "shared/lambda_layer/python")
standard_enhancement_path = os.path.join(
    backend_src, "handlers/events/standard_enhancement"
)
bedrock_enhancement_path = os.path.join(
    backend_src, "handlers/events/bedrock_enhancement"
)

sys.path.insert(0, shared_path)
sys.path.insert(0, standard_enhancement_path)
sys.path.insert(0, bedrock_enhancement_path)

# Import the real backend code
from shared.models.pulse import StopPulse
from standard_enhancement.app import handler as standard_enhancement_handler
from bedrock_enhancement.app import handler as bedrock_enhancement_handler


def create_test_pulse_data():
    """Create consistent test pulse data for both enhancements"""
    start_time = datetime.datetime.now(datetime.timezone.utc)
    stop_time = start_time + datetime.timedelta(hours=2)

    return StopPulse(
        user_id="comparison-test-user",
        pulse_id="comparison-pulse-123",
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


def test_standard_enhancement(pulse_data: StopPulse):
    """Test standard rule-based enhancement"""
    print(f"\n⚡ Testing STANDARD Enhancement...")

    # Mock lambda context
    class MockContext:
        def __init__(self):
            self.aws_request_id = "standard-test-123"
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

    # Create event structure for standard enhancement
    event = {
        "pulseData": pulse_data.model_dump(),
        "stopPulse": pulse_data.model_dump(),
        "aiEnhanced": False,
    }

    result = standard_enhancement_handler(event, context)
    print(f"✅ Standard enhancement completed")

    return {
        "type": "standard",
        "title": result.get("generatedTitle", "N/A"),
        "badge": result.get("generatedBadge", "N/A"),
        "ai_enhanced": result.get("aiEnhanced", False),
        "cost": 0,  # Standard enhancement is free
        "insights": None,  # Standard doesn't provide AI insights
    }


def test_bedrock_enhancement(pulse_data: StopPulse):
    """Test Bedrock AI enhancement (requires AWS_PROFILE)"""
    print(f"\n⚡ Testing BEDROCK Enhancement...")
    print("⚠️  Making REAL AWS Bedrock API calls - this will incur costs!")

    # Check if AWS_PROFILE is set
    if not os.environ.get("AWS_PROFILE"):
        print("❌ AWS_PROFILE environment variable not set!")
        print("   Skipping Bedrock test - set AWS_PROFILE to enable")
        return {
            "type": "bedrock",
            "title": "SKIPPED (No AWS_PROFILE)",
            "badge": "SKIPPED",
            "ai_enhanced": False,
            "cost": 0,
            "insights": "Skipped - AWS_PROFILE not set",
        }

    # Mock lambda context
    class MockContext:
        def __init__(self):
            self.aws_request_id = "bedrock-test-123"
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

    # Create event structure for Bedrock enhancement
    event = {
        "pulseData": pulse_data.model_dump(),
        "stopPulse": pulse_data.model_dump(),
        "aiSelected": True,
        "aiScore": 0.9,
    }

    try:
        result = bedrock_enhancement_handler(event, context)
        print(f"✅ Bedrock enhancement completed")

        enhanced_pulse = result.get("enhancedPulse", {})

        return {
            "type": "bedrock",
            "title": enhanced_pulse.get("gen_title", "N/A"),
            "badge": enhanced_pulse.get("gen_badge", "N/A"),
            "ai_enhanced": enhanced_pulse.get("ai_enhanced", False),
            "cost": result.get("aiCost", 0),
            "insights": enhanced_pulse.get("ai_insights", {}),
        }

    except Exception as e:
        print(f"❌ Bedrock enhancement failed: {e}")
        return {
            "type": "bedrock",
            "title": f"ERROR: {str(e)[:50]}...",
            "badge": "ERROR",
            "ai_enhanced": False,
            "cost": 0,
            "insights": f"Error: {str(e)}",
        }


def compare_enhancements():
    """Compare standard vs Bedrock enhancement results side by side"""

    print("🎯 PulseShrine Enhancement Comparison: Standard vs Bedrock")
    print("=" * 80)
    print("Testing the same pulse data through both enhancement pipelines")
    print("=" * 80)

    # Create shared test data
    pulse_data = create_test_pulse_data()

    print(f"\n📝 Test Input Data:")
    print(f"   Intent: {pulse_data.intent}")
    print(f"   Duration: {pulse_data.duration_seconds/3600:.1f} hours")
    print(f"   Intent Emotion: {pulse_data.intent_emotion}")
    print(f"   Reflection Emotion: {pulse_data.reflection_emotion}")
    print(f"   Reflection Length: {len(pulse_data.reflection)} characters")
    print(f"   Tags: {pulse_data.tags}")

    # Run both enhancements
    standard_result = test_standard_enhancement(pulse_data)
    bedrock_result = test_bedrock_enhancement(pulse_data)

    # SIDE-BY-SIDE COMPARISON
    print(f"\n📊 ENHANCEMENT COMPARISON RESULTS")
    print("=" * 80)

    print(f"\n🏷️  GENERATED TITLES:")
    print(f"   Standard: '{standard_result['title']}'")
    print(f"   Bedrock:  '{bedrock_result['title']}'")
    print(
        f"   Length Difference: {len(bedrock_result['title']) - len(standard_result['title'])} characters"
    )

    print(f"\n🏆 GENERATED BADGES:")
    print(f"   Standard: '{standard_result['badge']}'")
    print(f"   Bedrock:  '{bedrock_result['badge']}'")

    print(f"\n🧠 AI INSIGHTS:")
    print(f"   Standard: None (rule-based approach)")
    if isinstance(bedrock_result["insights"], dict):
        insights = bedrock_result["insights"]
        print(f"   Bedrock Insights:")
        print(f"     • Productivity Score: {insights.get('productivity_score', 'N/A')}")
        print(f"     • Key Insight: '{insights.get('key_insight', 'N/A')}'")
        print(f"     • Next Suggestion: '{insights.get('next_suggestion', 'N/A')}'")
        print(f"     • Mood Assessment: '{insights.get('mood_assessment', 'N/A')}'")
        print(f"     • Emotion Pattern: '{insights.get('emotion_pattern', 'N/A')}'")
    else:
        print(f"   Bedrock: {bedrock_result['insights']}")

    print(f"\n💰 COST COMPARISON:")
    print(f"   Standard: $0.000 (rule-based, no API calls)")
    print(f"   Bedrock:  ${bedrock_result['cost']/100:.3f} (AI-powered)")

    print(f"\n🎭 SOPHISTICATION ANALYSIS:")

    # Analyze title sophistication
    standard_title = standard_result["title"]
    bedrock_title = bedrock_result["title"]

    print(f"   Standard Approach:")
    print(f"     • Fast and consistent")
    print(f"     • Template-based generation")
    print(f"     • Uses emotion mapping rules")
    print(f"     • Cost-effective for high volume")

    print(f"   Bedrock Approach:")
    if "ERROR" not in bedrock_title and "SKIPPED" not in bedrock_title:
        print(f"     • Context-aware and creative")
        print(f"     • Understands content semantics")
        print(f"     • Provides actionable insights")
        print(f"     • Premium quality for important content")

        # Quality indicators
        has_insights = isinstance(bedrock_result["insights"], dict)
        title_longer = len(bedrock_title) > len(standard_title)
        mentions_content = any(
            word in bedrock_title.lower()
            for word in ["transformer", "ai", "breakthrough", "research"]
        )

        print(f"   Quality Indicators:")
        print(f"     ✅ AI Insights Generated: {has_insights}")
        print(
            f"     {'✅' if title_longer else '❌'} Title Sophistication: {'Higher' if title_longer else 'Similar'}"
        )
        print(
            f"     {'✅' if mentions_content else '❌'} Content Awareness: {'Yes' if mentions_content else 'No'}"
        )
    else:
        print(f"     • Could not test (see error above)")

    print(f"\n🏁 COMPARISON SUMMARY:")
    print("=" * 50)
    print(f"📋 Both approaches serve different use cases:")
    print(f"⚡ Standard: Ideal for high-volume, cost-sensitive processing")
    print(f"🧠 Bedrock: Perfect for premium content requiring deep understanding")
    print(f"🎯 Smart selection algorithm maximizes value and minimizes cost")

    return {
        "success": True,
        "standard": standard_result,
        "bedrock": bedrock_result,
        "value_demonstrated": "ERROR" not in bedrock_title
        and "SKIPPED" not in bedrock_title,
    }


def main():
    """Run the enhancement comparison test"""

    print("🧪 PulseShrine Enhancement Comparison Test")
    print("Direct comparison of Standard vs Bedrock enhancement quality")
    print("⚠️  NOTE: Bedrock test requires AWS_PROFILE set with valid credentials")
    print("=" * 80)

    try:
        result = compare_enhancements()

        if result["success"]:
            print(f"\n🏆 COMPARISON TEST COMPLETED!")

            if result["value_demonstrated"]:
                print(f"\n✅ Value Differentiation Demonstrated:")
                print(f"   • Standard provides fast, reliable baseline")
                print(f"   • Bedrock adds significant intelligence and insights")
                print(f"   • Clear justification for hybrid approach")
            else:
                print(f"\n⚠️  Limited Demonstration:")
                print(f"   • Standard enhancement tested successfully")
                print(f"   • Bedrock enhancement had issues (check AWS setup)")

            return 0
        else:
            print(f"\n❌ COMPARISON TEST FAILED!")
            return 1

    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
