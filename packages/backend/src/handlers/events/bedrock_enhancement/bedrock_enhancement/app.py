import json
import os
import boto3
from typing import Dict, Any, Optional
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from shared.models.pulse import StopPulse

# Import budget service for usage tracking
try:
    from shared.services.ai_budget_service import AIBudgetService
    from shared.ai_tracking.services.tracking_integration import AITrackingIntegration
except ImportError:
    # Fallback imports for local testing
    import sys
    import os

    sys.path.append(
        os.path.join(os.path.dirname(__file__), "../../shared/lambda_layer/python")
    )
    from shared.services.ai_budget_service import AIBudgetService
    from shared.ai_tracking.services.tracking_integration import AITrackingIntegration

# Initialize the logger
logger = Logger()

# Initialize budget service (will be lazy-loaded)
ai_usage_table_name = os.environ.get(
    "AI_USAGE_TRACKING_TABLE_NAME", "ps-ai-usage-tracking"
)
budget_service = AIBudgetService(ai_usage_table_name)

# Initialize tracking integration
tracking_integration = AITrackingIntegration(ai_usage_table_name)

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
    """Get AI configuration from Parameter Store with region-aware defaults and runtime fallback"""
    prefix = os.environ.get("PARAMETER_PREFIX", "/pulseshrine/ai/")

    # Get region-appropriate default model
    default_model = get_default_bedrock_model()

    # Get configured model from Parameter Store
    configured_model = get_parameter(f"{prefix}bedrock_model_id", default_model)

    # Test runtime availability and fallback if needed
    final_model = get_best_available_model(configured_model)

    return {
        "bedrock_model_id": final_model,
        "max_cost_cents": float(
            get_parameter(f"{prefix}max_cost_per_pulse_cents", "2")
        ),
        "enabled": get_parameter(f"{prefix}enabled", "true").lower() == "true",
    }


def get_default_bedrock_model() -> str:
    """Get region-appropriate default Bedrock model with fallback detection"""
    # Check if model is overridden via environment variable from CDK
    override_model = os.environ.get("DEFAULT_BEDROCK_MODEL_ID")
    if override_model:
        return override_model

    # Try to determine the current region
    current_region = os.environ.get("AWS_REGION")
    if not current_region:
        try:
            # Try to get region from boto3 session
            session = boto3.Session()
            current_region = session.region_name
        except Exception:
            current_region = "us-east-1"  # fallback

    # Region-specific model availability - using Nova Lite inference profiles
    region_models = {
        "us-east-1": "us.amazon.nova-lite-v1:0",
        "us-west-2": "us.amazon.nova-lite-v1:0",
        "eu-west-3": "eu.amazon.nova-lite-v1:0",
        "eu-west-1": "eu.amazon.nova-lite-v1:0",
        "ap-southeast-2": "apac.amazon.nova-lite-v1:0",
    }
    # Return region-specific model or universal fallback (Claude Haiku available everywhere)
    return region_models.get(current_region, "anthropic.claude-3-haiku-20240307-v1:0")


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
        "us.amazon.nova-lite-v1:0": 0.06,  # $0.06 per 1M input tokens
        "eu.amazon.nova-lite-v1:0": 0.06,  # $0.06 per 1M input tokens  
        "apac.amazon.nova-lite-v1:0": 0.06,  # $0.06 per 1M input tokens
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

    base_rate = base_pricing.get(model_id, 0.06)  # Default to Nova Lite pricing
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
            "temperature": 0.8,  # Higher creativity for more expressive outputs
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


def test_model_availability(model_id: str) -> bool:
    """Test if a Bedrock model is available and accessible"""
    if not bedrock_client:
        return False

    try:
        # Try a minimal test call
        test_prompt = "Test"
        if "nova" in model_id.lower():
            body = {
                "messages": [{"role": "user", "content": [{"text": test_prompt}]}],
                "inferenceConfig": {"maxTokens": 1, "temperature": 0.1},
            }
        elif "titan" in model_id.lower():
            body = {
                "inputText": test_prompt,
                "textGenerationConfig": {"maxTokenCount": 1, "temperature": 0.1},
            }
        else:  # Claude
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": test_prompt}],
                "temperature": 0.1,
            }

        bedrock_client.invoke_model(modelId=model_id, body=json.dumps(body))
        return True
    except Exception as e:
        logger.warning(f"Model {model_id} not available: {e}")
        return False


def get_best_available_model(preferred_model: str) -> str:
    """Get the best available model with runtime fallback"""
    # Test preferred model first
    if test_model_availability(preferred_model):
        return preferred_model

    # Fallback chain based on region and availability
    fallback_models = [
        # Try Claude Haiku (universally available)
        "anthropic.claude-3-haiku-20240307-v1:0",
        # Try US Nova Lite if available
        "us.amazon.nova-lite-v1:0",
        # Try EU Nova Lite if available  
        "eu.amazon.nova-lite-v1:0",
        # Try APAC Nova Lite if available
        "apac.amazon.nova-lite-v1:0",
    ]

    for model in fallback_models:
        if test_model_availability(model):
            logger.warning(
                f"Falling back to model: {model} (preferred {preferred_model} not available)"
            )
            return model

    # If nothing works, return the preferred anyway (will fail gracefully)
    logger.error("No Bedrock models available, returning preferred model")
    return preferred_model


def call_bedrock_nova(
    prompt: str, model_id: str, max_tokens: int = 200
) -> Optional[str]:
    """Call Bedrock Nova model with the given prompt"""
    try:
        body = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": 0.8,  # Higher creativity for more expressive outputs
                "topP": 0.9,
            },
        }

        response = bedrock_client.invoke_model(modelId=model_id, body=json.dumps(body))

        result = json.loads(response["body"].read())

        if "output" in result and "message" in result["output"]:
            return result["output"]["message"]["content"][0]["text"].strip()
        else:
            logger.error(f"Unexpected Nova response format: {result}")
            return None

    except Exception as e:
        logger.error(f"Error calling Bedrock Nova: {e}")
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
                "temperature": 0.8,  # Higher creativity for more expressive outputs
                "topP": 0.9,
            },
        }
        print(
            f"""calling bedrock with the following:
{model_id}
{json.dumps(body)}
"""
        )
        response = bedrock_client.invoke_model(modelId=model_id, body=json.dumps(body))

        result = json.loads(response["body"].read())

        if "results" in result and len(result["results"]) > 0:
            stripped_result = result["results"][0]["outputText"].strip()
            logger.error(f"Titan returned: {stripped_result}")
            return stripped_result
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
    # Enhanced sophisticated prompts for different models
    if "titan" in config["bedrock_model_id"].lower():
        # Even Titan gets more sophisticated prompt
        prompt = f"""Create an expressive, sophisticated title for this breakthrough session:

ACTIVITY: {stop_pulse.intent[:200]}
DURATION: {duration_minutes:.0f} minutes of deep work
EMOTIONAL ARC: {start_emotion} energy → {end_emotion} achievement
BREAKTHROUGH: {stop_pulse.reflection[:200]}

Create a title that captures:
- The specific technical achievement (not generic)
- The innovative nature of the work
- The emotional transformation
- Professional accomplishment tone

Examples of sophisticated titles:
🚀 Revolutionary AI Architecture: 2hr Breakthrough!
🧠 40% Performance Leap: Multimodal Transformer Success!
🔬 Novel Attention Mechanisms: Research Triumph!
💡 Breakthrough Session: Visual-Text AI Revolution!

Your sophisticated title (under 70 chars):"""
    else:
        # Highly sophisticated prompt for Claude/Nova models
        prompt = f"""Craft a sophisticated, expressive achievement title that captures the essence of this groundbreaking session:

DEEP WORK SESSION ANALYSIS:
• Activity: {stop_pulse.intent[:200]}
• Duration: {duration_minutes:.1f} minutes of focused innovation
• Emotional Journey: {start_emotion} mindset → {end_emotion} achievement
• Key Breakthrough: {stop_pulse.reflection[:200]}
• Tags: {', '.join(stop_pulse.tags or [])}

TITLE REQUIREMENTS:
• 50-70 characters (longer than basic titles)
• Sophisticated, professional language
• Capture specific technical achievement (not generic success)
• Include precise emotional transformation
• Reference concrete accomplishments from reflection
• Use power words: breakthrough, revolutionary, novel, pioneering
• 1 perfectly chosen emoji that matches the domain

SOPHISTICATED EXAMPLES:
• Research breakthrough: "🔬 Novel Transformer Architecture: 40% Multimodal Leap!"
• Technical innovation: "🚀 Revolutionary AI Reasoning: Visual-Text Breakthrough!"
• Scientific advance: "🧬 Pioneering Attention Mechanisms: 2hr Research Victory!"
• Engineering feat: "⚡ Breakthrough ML Pipeline: Performance Revolution!"

Analyze the reflection deeply and create a title that a world-class researcher would be proud to share. Focus on the specific innovation described.

TITLE:"""

    model_id = config["bedrock_model_id"]

    # Route to appropriate model with higher token limits for sophisticated output
    if "nova" in model_id.lower():
        result = call_bedrock_nova(prompt, model_id, max_tokens=150)
    elif "titan" in model_id.lower():
        result = call_bedrock_titan(prompt, model_id, max_tokens=150)
    else:
        # Fallback to Claude
        result = call_bedrock_claude(prompt, model_id, max_tokens=150)

    if result:
        # Clean up the result
        result = result.strip()
        
        # Handle Nova's verbose response format
        if "TITLE:" in result:
            # Extract the title part after "TITLE:"
            title_start = result.find("TITLE:") + len("TITLE:")
            result = result[title_start:].strip()
        
        # Take only the first line (Nova may add explanations)
        lines = result.split('\n')
        result = lines[0].strip()
        
        # Remove quotes if present
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        
        # Remove any prefixes like "Title:" or "SOPHISTICATED TITLE:"
        for prefix in ["Title:", "TITLE:", "title:", "SOPHISTICATED TITLE:"]:
            if result.startswith(prefix):
                result = result[len(prefix):].strip()
        
        # Allow longer titles (up to 120 chars for sophisticated titles)
        if len(result) > 120:
            result = result[:117] + "..."
        
        return result

    logger.error("Failed to generate pulse title from AI, using fallback")

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
    """Clean Titan/Nova response to extract raw JSON from formatted output."""
    import re

    # Remove common markdown formatting
    response = response.strip()
    
    # Handle Nova's verbose response format
    if "RAW JSON:" in response:
        # Extract the JSON part after "RAW JSON:"
        json_start = response.find("RAW JSON:") + len("RAW JSON:")
        response = response[json_start:].strip()
    
    # Also check for "JSON:" prefix
    if response.startswith("JSON:"):
        response = response[5:].strip()

    # Remove tabular-data-json wrapper if present
    if "tabular-data-json" in response:
        # Extract content between code blocks
        match = re.search(
            r"```(?:tabular-data-json|json)?\s*\n(.*?)\n```", response, re.DOTALL
        )
        if match:
            response = match.group(1).strip()

    # Remove any leading/trailing markdown code block markers
    response = re.sub(r"^```(?:json|tabular-data-json)?\s*\n?", "", response)
    response = re.sub(r"\n?```\s*$", "", response)

    # If response contains "rows" array (tabular format), extract the first row
    if '"rows"' in response and '"rows":' in response:
        try:
            # Parse the tabular format and extract first row
            tabular = json.loads(response)
            if "rows" in tabular and len(tabular["rows"]) > 0:
                return json.dumps(tabular["rows"][0])
        except Exception:
            pass

    # Try to extract JSON object from text
    json_match = re.search(r'\{[^}]*"productivity_score"[^}]*\}', response, re.DOTALL)
    if json_match:
        return json_match.group(0)

    # Try to find any JSON-like structure
    json_match = re.search(r"\{.*\}", response, re.DOTALL)
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

    prompt = f"""Analyze this breakthrough session and return sophisticated insights as RAW JSON:

DEEP SESSION ANALYSIS:
• Core Innovation: {stop_pulse.intent[:200]}
• Duration: {duration_minutes:.1f} minutes of focused excellence  
• Emotional Evolution: {start_emotion} → {end_emotion}
• Breakthrough Details: {stop_pulse.reflection[:200]}
• Technical Domain: {', '.join(stop_pulse.tags or [])}
{emotion_shift}

Generate sophisticated insights that reflect world-class expertise and breakthrough achievement.

RETURN ONLY this JSON structure with NO formatting, NO markdown, NO explanations:

{{
  "productivity_score": <number 1-10 based on breakthrough significance>,
  "key_insight": "<sophisticated technical insight, max 120 chars>",
  "next_suggestion": "<expert-level next step recommendation, max 140 chars>", 
  "mood_assessment": "<professional achievement assessment, max 60 chars>",
  "emotion_pattern": "<sophisticated emotional analysis, max 80 chars>"
}}

Examples of sophisticated insights:
- AI Research: "Revolutionary multimodal architecture achieved 40% performance breakthrough in visual-text reasoning"
- Technical Innovation: "Novel attention mechanisms demonstrate paradigm shift in transformer capabilities"
- Breakthrough Session: "Pioneering work establishes new benchmarks for AI system performance"

Focus on the SPECIFIC technical achievement described. Use professional, research-level language.

RAW JSON:"""

    model_id = config["bedrock_model_id"]

    # Route to appropriate model with higher token limits for sophisticated insights
    if "nova" in model_id.lower():
        result = call_bedrock_nova(prompt, model_id, max_tokens=600)
    elif "titan" in model_id.lower():
        result = call_bedrock_titan(prompt, model_id, max_tokens=600)
    else:
        result = call_bedrock_claude(prompt, model_id, max_tokens=600)

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
            logger.warning(
                f"Cleaned result was: {cleaned_result if 'cleaned_result' in locals() else 'N/A'}"
            )
    logger.error("Failed to generate insights from AI, using fallback")

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


def generate_ai_badge(pulse_values: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Generate AI-powered badge: icon + 2 words based on content and emotions"""
    stop_pulse = StopPulse(**pulse_values)
    duration_minutes = stop_pulse.actual_duration_seconds // 60 or 1

    # Create context for badge generation
    start_emotion = stop_pulse.intent_emotion or "focused"
    end_emotion = stop_pulse.reflection_emotion or "accomplished"

    prompt = f"""Generate a prestigious achievement badge for this session.

SESSION DETAILS:
- Work: {stop_pulse.intent[:200]}
- Duration: {duration_minutes} minutes
- Result: {stop_pulse.reflection[:200]}

REQUIRED OUTPUT FORMAT:
Return ONLY the badge in this exact format:
[emoji] [Word1] [Word2]

Examples of CORRECT output:
🧠 Neural Architect
🚀 Algorithm Pioneer
📊 Data Visionary
⚡ Code Revolutionary
🔬 Research Champion

RULES:
- Start with ONE emoji
- Follow with exactly 2-3 words
- Use sophisticated terms: Pioneer, Architect, Visionary, Revolutionary, Champion, Genius, Master
- NO markdown, NO formatting, NO explanations
- NO "BADGE:" prefix
- NO analysis or extra text

Your badge:"""

    model_id = config["bedrock_model_id"]

    # Route to appropriate model with sufficient tokens for badge generation
    if "nova" in model_id.lower():
        result = call_bedrock_nova(prompt, model_id, max_tokens=60)
    elif "titan" in model_id.lower():
        result = call_bedrock_titan(prompt, model_id, max_tokens=60)
    else:
        result = call_bedrock_claude(prompt, model_id, max_tokens=60)

    if result:
        # Clean up the result aggressively for Nova's verbose responses
        result = result.strip()
        
        # Remove all markdown formatting
        import re
        result = re.sub(r'\*\*([^*]+)\*\*', r'\1', result)  # Remove **bold**
        result = re.sub(r'\*([^*]+)\*', r'\1', result)      # Remove *italic*
        
        # Handle various Nova verbose patterns
        verbose_patterns = [
            "PRESTIGIOUS BADGE:",
            "**PRESTIGIOUS BADGE:**", 
            "Your badge:",
            "Badge:",
            "BADGE:",
            "Analysis:",
            "**Analysis:**"
        ]
        
        for pattern in verbose_patterns:
            if pattern in result:
                # Extract content after the pattern
                parts = result.split(pattern, 1)
                if len(parts) > 1:
                    result = parts[1].strip()
        
        # Split into lines and find the badge line
        lines = [line.strip() for line in result.split('\n') if line.strip()]
        
        for line in lines:
            # Skip empty lines or lines that are clearly explanations
            if not line or line.startswith('-') or line.startswith('•') or 'Core Work:' in line or 'Analysis:' in line:
                continue
                
            # Look for emoji + words pattern
            parts = line.split()
            if len(parts) >= 2 and len(parts) <= 4:
                # Check if first part looks like an emoji (unicode chars)
                first_part = parts[0]
                if len(first_part) <= 4 and any(ord(char) > 127 for char in first_part):
                    # This looks like a valid badge format
                    result = ' '.join(parts)
                    break
        
        # Final cleanup - remove any remaining formatting
        result = re.sub(r'[*_`]', '', result)  # Remove markdown chars
        result = result.strip()
        
        # Validate final format (emoji + 2-3 words)
        parts = result.split()
        if len(parts) >= 2 and len(parts) <= 4:
            # Check if first part is likely an emoji
            if len(parts[0]) <= 4 and any(ord(char) > 127 for char in parts[0]):
                return ' '.join(parts)

    logger.error("Failed to generate pulse badge from AI, using fallback")

    # Emotion-aware fallback badge based on activity analysis
    activity_keywords = {
        "code": "💻",
        "programming": "💻",
        "development": "💻",
        "software": "💻",
        "research": "🔬",
        "study": "📚",
        "learning": "📚",
        "analysis": "🔍",
        "design": "🎨",
        "creative": "🎨",
        "art": "🎨",
        "visual": "🎨",
        "writing": "✍️",
        "content": "✍️",
        "blog": "✍️",
        "documentation": "✍️",
        "meeting": "🤝",
        "collaboration": "🤝",
        "team": "🤝",
        "discussion": "🤝",
        "planning": "📋",
        "strategy": "📋",
        "organizing": "📋",
        "project": "📋",
    }

    # Find activity type
    activity_text = (stop_pulse.intent + " " + stop_pulse.reflection).lower()
    activity_emoji = "⚡"  # default

    for keyword, emoji in activity_keywords.items():
        if keyword in activity_text:
            activity_emoji = emoji
            break

    # Emotion-based second word
    emotion_words = {
        "breakthrough": "Breakthrough",
        "accomplished": "Champion",
        "fulfilled": "Master",
        "energized": "Dynamo",
        "innovative": "Pioneer",
        "creative": "Genius",
        "focused": "Laser",
        "productive": "Machine",
        "successful": "Hero",
    }

    emotion_word = emotion_words.get(end_emotion, "Achiever")

    # Activity-based first word
    if "code" in activity_text or "programming" in activity_text:
        activity_word = "Code"
    elif "research" in activity_text or "analysis" in activity_text:
        activity_word = "Research"
    elif "design" in activity_text or "creative" in activity_text:
        activity_word = "Creative"
    elif "writing" in activity_text:
        activity_word = "Writing"
    elif "learning" in activity_text or "study" in activity_text:
        activity_word = "Learning"
    else:
        activity_word = "Productivity"

    return f"{activity_emoji} {activity_word} {emotion_word}"


def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda function handler for Bedrock enhancement.

    Input: Event with pulse data and aiWorthy flag
    Output: Enhanced event with AI-generated content
    """
    logger.info("Bedrock Enhancement Lambda invoked")

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

        # Estimate cost before processing (title + badge + insights = 3 API calls with higher token limits)
        text_length = len(str(pulse_values["intent"]) + str(pulse_values["reflection"]))
        base_cost = estimate_bedrock_cost(text_length, config["bedrock_model_id"])
        # Multiply by 4 for title + badge + insights generation with sophisticated prompts
        estimated_cost_cents = base_cost * 4 * 100

        if estimated_cost_cents > config["max_cost_cents"]:
            logger.warning(
                f"Estimated cost {estimated_cost_cents:.4f} cents exceeds limit {config['max_cost_cents']}"
            )
            return {**event, "enhanced": False, "reason": "Cost limit exceeded"}

        # Start tracking the enhancement
        user_id = pulse_values.get("user_id", "unknown")
        pulse_id = pulse_values.get("pulse_id", "unknown")
        
        # Estimate tokens for tracking
        estimated_input_tokens = text_length // 4  # rough approximation
        estimated_output_tokens = 400  # estimate for title + badge + insights
        
        event_id = tracking_integration.start_enhancement_tracking(
            user_id=user_id,
            pulse_id=pulse_id,
            model_id=config["bedrock_model_id"],
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            metadata={
                "enhancement_type": "full",  # title + badge + insights
                "intent_emotion": pulse_values.get("intent_emotion"),
                "reflection_emotion": pulse_values.get("reflection_emotion"),
            }
        )
        
        from datetime import datetime
        start_time = datetime.now()

        try:
            # Generate AI enhancements
            enhanced_title = enhance_pulse_title(pulse_values, config)
            ai_badge = generate_ai_badge(pulse_values, config)
            ai_insights = generate_ai_insights(pulse_values, config)
            
            # Calculate actual processing time
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Complete tracking successfully
            if event_id and user_id != "unknown":
                actual_input_tokens = estimated_input_tokens  # Could be more precise with actual token counting
                actual_output_tokens = len(enhanced_title + ai_badge + str(ai_insights)) // 4
                
                actual_cost_cents = tracking_integration.complete_enhancement_tracking(
                    event_id=event_id,
                    user_id=user_id,
                    model_id=config["bedrock_model_id"],
                    input_tokens=actual_input_tokens,
                    output_tokens=actual_output_tokens,
                    duration_ms=duration_ms,
                    response_metadata={
                        "title_generated": bool(enhanced_title),
                        "badge_generated": bool(ai_badge),
                        "insights_generated": bool(ai_insights),
                        "enhancement_success": True,
                    }
                )
                
                # Use actual cost if available, otherwise fall back to estimate
                if actual_cost_cents is not None:
                    final_cost_cents = actual_cost_cents
                else:
                    final_cost_cents = estimated_cost_cents

        except Exception as enhancement_error:
            # Track the failure
            if event_id and user_id != "unknown":
                tracking_integration.fail_enhancement_tracking(
                    event_id=event_id,
                    user_id=user_id,
                    error_code="ENHANCEMENT_FAILED",
                    error_message=str(enhancement_error),
                    duration_ms=int((datetime.now() - start_time).total_seconds() * 1000) if 'start_time' in locals() else None
                )
            raise enhancement_error

        # Set default cost if not set from tracking
        if 'final_cost_cents' not in locals():
            final_cost_cents = estimated_cost_cents

        # Record AI usage and trigger rewards - use actual cost with full precision
        if user_id != "unknown":
            try:
                usage_result = budget_service.record_ai_enhancement(
                    user_id,
                    final_cost_cents,  # Use actual cost with full precision
                    pulse_data,  # Pass pulse data for reward analysis
                )
                logger.info(f"Recorded AI usage for user {user_id}: {usage_result}")

                # Add rewards to pulse data if any were triggered
                if usage_result.get("rewards"):
                    pulse_data["triggered_rewards"] = usage_result["rewards"]

            except Exception as e:
                logger.warning(f"Failed to record AI usage for user {user_id}: {e}")

        # Prepare enhanced pulse data
        enhanced_pulse = {
            **pulse_data,
            "gen_title": enhanced_title,
            "gen_badge": ai_badge,
            "ai_enhanced": True,
            "ai_insights": ai_insights,
            "ai_cost_cents": final_cost_cents,  # Store with 4 decimal precision
        }

        result = {
            **event,
            "enhanced": True,
            "enhancedPulse": enhanced_pulse,
            "aiCost": final_cost_cents,  # Return with 4 decimal precision
        }

        logger.info(
            f"Successfully enhanced pulse {pulse_values['pulse_id']} "
            f"with title: '{enhanced_title}' (cost: {final_cost_cents:.4f}¢)"
        )

        return result

    except Exception as e:
        logger.error(f"Error in Bedrock enhancement: {e}")
        return {**event, "enhanced": False, "error": str(e)}
