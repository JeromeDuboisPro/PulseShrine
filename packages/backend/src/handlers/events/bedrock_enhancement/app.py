import json
import os
import boto3
from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from shared.models.pulse import StopPulse

# Initialize the logger
logger = Logger()

# Initialize AWS clients - use default region from environment/credentials
try:
    bedrock_client = boto3.client("bedrock-runtime")
    ssm_client = boto3.client("ssm")
except Exception as e:
    logger.error(f"Failed to initialize AWS clients: {e}")
    bedrock_client = None
    ssm_client = boto3.client("ssm")

# Cache for parameters
parameter_cache = {}


def get_parameter(parameter_name: str, default_value: str = "") -> str:
    """Get parameter from Parameter Store with caching"""
    if parameter_name in parameter_cache:
        return parameter_cache[parameter_name]

    try:
        response = ssm_client.get_parameter(Name=parameter_name)
        value = response["Parameter"]["Value"]
        parameter_cache[parameter_name] = value
        return value
    except Exception as e:
        logger.warning(f"Failed to get parameter {parameter_name}: {e}")
        return default_value


def get_ai_config() -> Dict[str, Any]:
    """Get AI configuration from Parameter Store with region-aware defaults"""
    prefix = os.environ.get("PARAMETER_PREFIX", "/pulseshrine/ai/")

    # Get region-appropriate default model
    default_model = get_default_bedrock_model()

    return {
        "bedrock_model_id": get_parameter(f"{prefix}bedrock_model_id", default_model),
        "max_cost_cents": float(
            get_parameter(f"{prefix}max_cost_per_pulse_cents", "2")
        ),
        "enabled": get_parameter(f"{prefix}enabled", "true").lower() == "true",
    }


def get_default_bedrock_model() -> str:
    """Get region-appropriate default Bedrock model"""
    # Try to determine the current region
    current_region = os.environ.get("AWS_REGION")
    if not current_region:
        try:
            # Try to get region from boto3 session
            session = boto3.Session()
            current_region = session.region_name
        except Exception:
            current_region = "us-east-1"  # fallback

    # Region-specific model availability
    region_models = {
        "us-east-1": "amazon.titan-text-express-v1",
        "us-west-2": "amazon.titan-text-express-v1",
        "eu-west-3": "amazon.titan-text-express-v1",
        "eu-west-1": "amazon.titan-text-express-v1",
        "ap-southeast-2": "amazon.titan-text-express-v1",
    }

    # Return region-specific model or default fallback
    return region_models.get(current_region, "amazon.titan-text-express-v1")


def extract_pulse_values(pulse_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract values from pulse data, handling DynamoDB format"""

    def get_value(key: str, default=None):
        if key in pulse_data:
            value = pulse_data[key]
            if isinstance(value, dict):
                # DynamoDB format like {'S': 'value'} or {'N': '123'}
                if "S" in value:
                    return value["S"]
                elif "N" in value:
                    return float(value["N"])
                elif "BOOL" in value:
                    return value["BOOL"]
            return value
        return default

    return {
        "pulse_id": get_value("pulse_id", ""),
        "user_id": get_value("user_id", ""),
        "intent": get_value("intent", ""),
        "reflection": get_value("reflection", ""),
        "duration_seconds": get_value("duration_seconds")
        or get_value("actual_duration_seconds", 0),
        "intent_emotion": get_value("intent_emotion", ""),
        "reflection_emotion": get_value("reflection_emotion", ""),
        "start_time": get_value("start_time", ""),
        "stopped_at": get_value("stopped_at", ""),
    }


def estimate_bedrock_cost(text_length: int, model_id: str) -> float:
    """Estimate cost for Bedrock API call with region-aware pricing"""
    # Rough token estimation (1 token ≈ 0.75 characters)
    estimated_tokens = text_length * 0.8

    # Base pricing per 1M tokens (may vary by region)
    base_pricing = {
        "amazon.titan-text-express-v1": 0.13,  # $0.13 per 1M input tokens
        "anthropic.claude-3-haiku-20240307-v1:0": 0.25,  # $0.25 per 1M input tokens
    }

    # Get region for potential regional pricing adjustments
    current_region = os.environ.get("AWS_REGION", "us-east-1")

    # Regional pricing multipliers (if different from base pricing)
    regional_multipliers = {
        "eu-west-3": 1.0,  # Same as base pricing
        "us-east-1": 1.0,  # Base region pricing
        "us-west-2": 1.0,  # Same as base pricing
        "eu-west-1": 1.0,  # Same as base pricing
        "ap-southeast-2": 1.0,  # Same as base pricing
    }

    base_rate = base_pricing.get(model_id, 0.13)  # Default to Titan Express pricing
    regional_multiplier = regional_multipliers.get(current_region, 1.0)

    estimated_cost = (estimated_tokens / 1_000_000) * base_rate * regional_multiplier

    return estimated_cost


def call_bedrock_claude(
    prompt: str, model_id: str, max_tokens: int = 200
) -> Optional[str]:
    """Call Bedrock Claude model with the given prompt"""
    try:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }

        response = bedrock_client.invoke_model(modelId=model_id, body=json.dumps(body))

        result = json.loads(response["body"].read())

        if "content" in result and len(result["content"]) > 0:
            return result["content"][0]["text"].strip()
        else:
            logger.error(f"Unexpected Bedrock response format: {result}")
            return None

    except Exception as e:
        logger.error(f"Error calling Bedrock: {e}")
        return None


def call_bedrock_titan(
    prompt: str, model_id: str, max_tokens: int = 200
) -> Optional[str]:
    """Call Bedrock Titan model with the given prompt"""
    try:
        body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
                "temperature": 0.7,
                "topP": 0.9,
            },
        }

        response = bedrock_client.invoke_model(modelId=model_id, body=json.dumps(body))

        result = json.loads(response["body"].read())

        if "results" in result and len(result["results"]) > 0:
            return result["results"][0]["outputText"].strip()
        else:
            logger.error(f"Unexpected Titan response format: {result}")
            return None

    except Exception as e:
        logger.error(f"Error calling Bedrock Titan: {e}")
        return None


def enhance_pulse_title(pulse_values: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Generate AI-enhanced title using Bedrock with emotion context"""
    stop_pulse = StopPulse(**pulse_values)
    duration_minutes = stop_pulse.actual_duration_seconds // 60 or 1

    # Create emotion context
    start_emotion = stop_pulse.intent_emotion or "focused"
    end_emotion = stop_pulse.reflection_emotion or "accomplished"

    emotion_journey = ""
    if start_emotion != end_emotion:
        emotion_journey = (
            f"\nEmotion Journey: Started {start_emotion} → Ended {end_emotion}"
        )
    else:
        emotion_journey = f"\nConsistent Energy: {start_emotion} throughout"

    prompt = f"""Create an engaging, personalized title for this productivity session:

Activity: {stop_pulse.intent}
Duration: {duration_minutes:.1f} minutes
Starting Energy: {start_emotion}
Reflection: {stop_pulse.reflection}
Final Emotion: {end_emotion}{emotion_journey}

Requirements:
- Keep it under 60 characters
- Make it motivational and personal  
- Include 1 relevant emoji that matches the emotional journey
- Focus on achievement and progress
- Reflect the emotional transformation (if any)
- Be specific about the accomplishment

Emotion-Based Examples:
- If started focused → ended accomplished: "🎯 Laser-Focused {duration_minutes:.0f}min Success!"
- If started creation → ended fulfilled: "💡 Creative Breakthrough Achieved!"
- If started study → ended energized: "📚 Knowledge Boost Complete!"
- If stayed consistent: "⚡ Sustained {start_emotion.title()} Energy Session"

Return only the title, no Here's the title based on the provide information, really nothing else but a single raw title."""

    model_id = config["bedrock_model_id"]

    # Try Titan first (our primary model)
    if "titan" in model_id.lower():
        result = call_bedrock_titan(prompt, model_id, max_tokens=80)
    else:
        # Fallback to Claude
        result = call_bedrock_claude(prompt, model_id, max_tokens=80)

    if result:
        # Clean up the result
        result = result.strip()
        # Remove quotes if present
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        return result

    # Emotion-aware fallback title
    start_emotion = stop_pulse.intent_emotion or "focused"
    end_emotion = stop_pulse.reflection_emotion or "accomplished"

    # Emotion-based emoji selection
    emotion_emojis = {
        "focus": "🎯",
        "focused": "🎯",
        "creation": "💡",
        "creative": "💡",
        "study": "📚",
        "learning": "📚",
        "work": "💼",
        "productive": "💼",
        "brainstorm": "🧠",
        "thinking": "🧠",
        "reflection": "🤔",
        "contemplative": "🤔",
        "energized": "⚡",
        "excited": "⚡",
        "accomplished": "🏆",
        "fulfilled": "🏆",
        "peaceful": "🕯️",
        "calm": "🕯️",
        "grounded": "🌿",
        "centered": "🌿",
    }

    # Choose emoji based on end emotion, fallback to start emotion
    emoji = emotion_emojis.get(
        end_emotion.lower(), emotion_emojis.get(start_emotion.lower(), "⚡")
    )

    # Create emotion-aware title
    if start_emotion != end_emotion:
        return f"{emoji} {pulse_values['intent']} → {end_emotion.title()}"
    else:
        return f"{emoji} {start_emotion.title()} {pulse_values['intent']} Session"


def clean_titan_json_response(response: str) -> str:
    """Clean Titan response to extract raw JSON from formatted output."""
    import re
    
    # Remove common markdown formatting
    response = response.strip()
    
    # Remove tabular-data-json wrapper if present
    if "tabular-data-json" in response:
        # Extract content between code blocks
        match = re.search(r'```(?:tabular-data-json|json)?\s*\n(.*?)\n```', response, re.DOTALL)
        if match:
            response = match.group(1).strip()
    
    # Remove any leading/trailing markdown code block markers
    response = re.sub(r'^```(?:json|tabular-data-json)?\s*\n?', '', response)
    response = re.sub(r'\n?```\s*$', '', response)
    
    # If response contains "rows" array (tabular format), extract the first row
    if '"rows"' in response and '"rows":' in response:
        try:
            # Parse the tabular format and extract first row
            tabular = json.loads(response)
            if "rows" in tabular and len(tabular["rows"]) > 0:
                return json.dumps(tabular["rows"][0])
        except:
            pass
    
    # Try to extract JSON object from text
    json_match = re.search(r'\{[^}]*"productivity_score"[^}]*\}', response, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    # Try to find any JSON-like structure
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return response.strip()


def generate_ai_insights(
    pulse_values: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate AI insights with emotion-driven analysis"""

    stop_pulse = StopPulse(**pulse_values)
    duration_minutes = stop_pulse.actual_duration_seconds // 60 or 1
    start_emotion = stop_pulse.intent_emotion or "focused"
    end_emotion = stop_pulse.reflection_emotion or "accomplished"

    # Emotion journey analysis
    emotion_shift = ""
    if start_emotion != end_emotion:
        emotion_shift = f"\nEmotional Transformation: {start_emotion} → {end_emotion}"
    else:
        emotion_shift = (
            f"\nConsistent Emotional State: {start_emotion} maintained throughout"
        )

    prompt = f"""Analyze this productivity session and return ONLY a JSON object with no formatting:

Activity: {stop_pulse.intent}
Duration: {duration_minutes:.1f} minutes  
Starting Energy: {start_emotion}
Reflection: {stop_pulse.reflection}
Final Emotion: {end_emotion}{emotion_shift}

CRITICAL: Return ONLY the JSON object below. No markdown, no tables, no explanations, no wrapping.
Start your response with {{ and end with }}. Nothing else.

{{
  "productivity_score": <number 1-10>,
  "key_insight": "<max 100 chars>",
  "next_suggestion": "<max 120 chars>", 
  "mood_assessment": "<max 50 chars>",
  "emotion_pattern": "<max 60 chars>"
}}

Examples for reference:
- focus→accomplished: "Strong focus led to clear achievement"
- creation→frustrated: "Creative energy needs better structure"
- study→energized: "Learning boosted motivation effectively"

RETURN ONLY RAW JSON. NO OTHER TEXT."""

    model_id = config["bedrock_model_id"]

    # Try Titan first (our primary model)
    if "titan" in model_id.lower():
        result = call_bedrock_titan(prompt, model_id, max_tokens=400)
    else:
        result = call_bedrock_claude(prompt, model_id, max_tokens=400)

    if result:
        try:
            # Clean the response to extract JSON
            cleaned_result = clean_titan_json_response(result)
            insights = json.loads(cleaned_result)
            required_keys = [
                "productivity_score",
                "key_insight",
                "next_suggestion",
                "mood_assessment",
            ]
            if all(key in insights for key in required_keys):
                return insights
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse AI insights JSON: {result}")
            logger.warning(f"Cleaned result was: {cleaned_result if 'cleaned_result' in locals() else 'N/A'}")

    # Emotion-aware fallback insights
    base_score = min(10, max(1, int(duration_minutes / 6)))
    emotion_bonus = (
        1
        if end_emotion in ["accomplished", "fulfilled", "energized", "peaceful"]
        else 0
    )
    score = min(10, base_score + emotion_bonus)

    # Emotion-aware insights
    if start_emotion != end_emotion:
        key_insight = f"Emotional journey: {start_emotion} → {end_emotion} in {duration_minutes:.0f}min"
        emotion_pattern = f"{start_emotion} evolved to {end_emotion}"
    else:
        key_insight = f"Maintained {start_emotion} energy for {duration_minutes:.0f}min"
        emotion_pattern = f"Consistent {start_emotion} state"

    # Emotion-based suggestions
    suggestion_map = {
        "frustrated": "Try shorter sessions or clearer goals next time",
        "tired": "Consider taking breaks or adjusting session timing",
        "accomplished": "Great work! Try increasing session length gradually",
        "energized": "Channel this energy into your next challenge",
        "peaceful": "This calm state is perfect for reflection sessions",
        "focused": "Excellent focus! Maintain this momentum",
    }

    suggestion = suggestion_map.get(
        end_emotion, "Continue building on this positive momentum"
    )

    return {
        "productivity_score": score,
        "key_insight": key_insight,
        "next_suggestion": suggestion,
        "mood_assessment": f"{end_emotion} with {start_emotion} foundation",
        "emotion_pattern": emotion_pattern,
    }


def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda function handler for Bedrock enhancement.

    Input: Event with pulse data and aiWorthy flag
    Output: Enhanced event with AI-generated content
    """
    logger.info(f"Bedrock Enhancement Lambda invoked")

    try:
        # Check if Bedrock client is available
        if bedrock_client is None:
            logger.warning("Bedrock client not available in this region")
            return {**event, "enhanced": False, "reason": "Bedrock not available"}

        # Get AI configuration
        config = get_ai_config()

        if not config["enabled"]:
            logger.info("AI enhancement is disabled")
            return {**event, "enhanced": False, "reason": "AI disabled"}

        # Extract pulse data
        pulse_data = event.get("pulseData", {})
        if not pulse_data:
            logger.error("No pulse data found in event")
            return {**event, "enhanced": False, "reason": "No pulse data"}

        pulse_values = extract_pulse_values(pulse_data)
        logger.info(f"Enhancing pulse: {pulse_values['pulse_id']}")

        # Estimate cost before processing
        text_length = len(str(pulse_values["intent"]) + str(pulse_values["reflection"]))
        estimated_cost = estimate_bedrock_cost(text_length, config["bedrock_model_id"])
        estimated_cost_cents = estimated_cost * 100

        if estimated_cost_cents > config["max_cost_cents"]:
            logger.warning(
                f"Estimated cost {estimated_cost_cents:.2f} cents exceeds limit {config['max_cost_cents']}"
            )
            return {**event, "enhanced": False, "reason": "Cost limit exceeded"}

        # Generate AI enhancements
        enhanced_title = enhance_pulse_title(pulse_values, config)
        ai_insights = generate_ai_insights(pulse_values, config)

        # Prepare enhanced pulse data
        enhanced_pulse = {
            **pulse_data,
            "gen_title": enhanced_title,
            "gen_badge": f"🤖 AI Enhanced",  # Special badge for AI-enhanced pulses
            "ai_enhanced": True,
            "ai_insights": ai_insights,
            "ai_cost_cents": estimated_cost_cents,
        }

        result = {
            **event,
            "enhanced": True,
            "enhancedPulse": enhanced_pulse,
            "aiCost": estimated_cost_cents,
        }

        logger.info(
            f"Successfully enhanced pulse {pulse_values['pulse_id']} "
            f"with title: '{enhanced_title}' (cost: {estimated_cost_cents:.2f}¢)"
        )

        return result

    except Exception as e:
        logger.error(f"Error in Bedrock enhancement: {e}")
        return {**event, "enhanced": False, "error": str(e)}
