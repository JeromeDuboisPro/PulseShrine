import os
from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import (
    DynamoDBRecord,
)
import boto3
from typing import Dict, Any
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import (
    DynamoDBStreamEvent,
)
from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import (
    DynamoDBRecordEventName,
)

# Import enhanced services
try:
    from shared.services.ai_budget_service import AIBudgetService
    from shared.services.worthiness_service import (
        WorthinessCalculator,
        EXCEPTIONAL_THRESHOLD,
        GOOD_THRESHOLD,
    )
    from shared.ai_tracking.services.tracking_integration import AITrackingIntegration
    from shared.utils.app_with_tracking import app_with_tracking
except ImportError:
    # Fallback imports for local testing
    import sys
    import os

    sys.path.append(
        os.path.join(os.path.dirname(__file__), "../../shared/lambda_layer/python")
    )
    from shared.services.ai_budget_service import AIBudgetService
    from shared.services.worthiness_service import (
        WorthinessCalculator,
        EXCEPTIONAL_THRESHOLD,
        GOOD_THRESHOLD,
    )
    from shared.ai_tracking.services.tracking_integration import AITrackingIntegration
    from shared.utils.app_with_tracking import app_with_tracking

# Initialize the logger
logger = Logger()

# Initialize SSM client
ssm_client = boto3.client("ssm")

# Cache for parameters to reduce API calls
parameter_cache = {}

# Initialize services (will be lazy-loaded)
ai_usage_table_name = os.environ.get(
    "AI_USAGE_TRACKING_TABLE_NAME", "ps-ai-usage-tracking"
)
budget_service = AIBudgetService(ai_usage_table_name)
worthiness_calculator = WorthinessCalculator(budget_service)

# Initialize tracking integration
tracking_integration = AITrackingIntegration(ai_usage_table_name)


def get_parameter(parameter_name: str, default_value: str = "0") -> str:
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


def get_ai_config() -> Dict[str, float]:
    """Get AI configuration from Parameter Store"""
    prefix = os.environ.get("PARAMETER_PREFIX", "/pulseshrine/ai/")

    return {
        "max_cost_cents": float(
            get_parameter(f"{prefix}max_cost_per_pulse_cents", "2")
        ),
        "enabled": get_parameter(f"{prefix}enabled", "true").lower() == "true",
        "bedrock_model_id": get_parameter(
            f"{prefix}bedrock_model_id", "us.amazon.nova-lite-v1:0"
        ),
    }


def extract_pulse_data_from_record(record: DynamoDBRecord) -> Dict[str, Any]:
    """Extract pulse data from a single DynamoDB record using Powertools"""
    try:
        # Only process INSERT events
        if record.event_name != DynamoDBRecordEventName.INSERT:
            logger.info(
                f"Skipping {record.event_name} event for record {record.event_id}"
            )
            return {}

        # Extract the new image (already deserialized by Powertools to Python format)
        new_image = record.dynamodb.new_image if record.dynamodb else {}

        if new_image:
            logger.info(
                f"Processing INSERT event - extracted pulse data from record {record.event_id}"
            )
            return new_image

        logger.warning(f"No new image found in INSERT record {record.event_id}")
        return {}

    except Exception as e:
        logger.error(f"Error extracting pulse data from record: {e}")
        return {}


def parse_event(event) -> DynamoDBStreamEvent:
    """Parse event using Powertools data classes with fallback"""
    try:
        # Handle list input from EventBridge Pipes
        if isinstance(event, list):
            # Wrap in Records format that DynamoDBStreamEvent expects
            wrapped_event = {"Records": event}
            return DynamoDBStreamEvent(wrapped_event)

        # Handle dict input (standard DynamoDB stream format)
        elif isinstance(event, dict):
            return DynamoDBStreamEvent(event)

        else:
            raise ValueError(f"Unsupported event type: {type(event)}")

    except Exception as e:
        logger.error(f"Error parsing event with Powertools: {e}")
        # Fallback to manual parsing for non-standard formats
        raise


def estimate_enhancement_cost(
    pulse_data: Dict[str, Any], config: Dict[str, float]
) -> float:
    """Estimate the cost in cents for AI enhancement based on content length"""
    try:
        intent = str(pulse_data.get("intent", ""))
        reflection = str(pulse_data.get("reflection", ""))
        total_chars = len(intent) + len(reflection)
        
        # Frontend enforces max 200 chars each, so total max is 400 chars
        # Cap at actual maximum possible length
        total_chars = min(total_chars, 400)

        # Estimate input tokens (rough approximation: 4 chars per token)
        estimated_input_tokens = max(total_chars // 4, 1)  # Minimum 1 token
        
        # For short content (400 chars max), output will be proportionally smaller
        # Estimate ~150-300 tokens output based on input length
        estimated_output_tokens = min(50 + (estimated_input_tokens * 2), 300)

        # Nova Lite pricing: $0.00006 per 1K input tokens, $0.00024 per 1K output tokens
        input_cost_dollars = (estimated_input_tokens / 1000) * 0.00006
        output_cost_dollars = (estimated_output_tokens / 1000) * 0.00024
        
        total_cost_dollars = input_cost_dollars + output_cost_dollars
        total_cost_cents = total_cost_dollars * 100  # Convert to cents
        
        # Add small buffer for processing overhead
        total_cost_cents += 0.01

        # Cap at configured maximum
        max_cost = float(config.get("max_cost_cents", 2.0))
        final_cost = min(total_cost_cents, max_cost)
        
        logger.debug(
            f"Cost estimation: {total_chars} chars → {estimated_input_tokens} input + {estimated_output_tokens} output tokens → {final_cost:.4f} cents"
        )
        
        return round(final_cost, 4)  # Round to 4 decimal places for 0.0001 cent precision

    except Exception as e:
        logger.warning(f"Error estimating cost: {e}")
        return float(config.get("max_cost_cents", 2.0))  # Use max as fallback


def should_enhance_with_ai(
    pulse_data: Dict[str, Any], config: Dict[str, float], user_id: str
) -> tuple[bool, str, Dict[str, Any]]:
    """Determine if pulse should be enhanced with AI using value-first budget approach"""

    if not config["enabled"]:
        logger.info("AI enhancement is disabled")
        return False, "AI enhancement disabled", {}

    try:
        # Calculate worthiness score using enhanced algorithm
        worthiness_score = worthiness_calculator.calculate_worthiness(
            pulse_data, user_id
        )

        # Estimate cost for this enhancement
        estimated_cost_cents = estimate_enhancement_cost(pulse_data, config)

        # Debug: Check if user exists in ps-users table
        try:
            user_plan = budget_service.user_service.get_user_plan(user_id)
            logger.info(f"User {user_id} plan: {user_plan}")
        except Exception as e:
            logger.error(f"Error getting user plan for debug: {e}")

        # Check budget availability
        can_afford, budget_reason, usage_info = budget_service.can_afford_enhancement(
            user_id, estimated_cost_cents
        )

        if not can_afford:
            logger.info(
                f"Budget check failed for user {user_id}: {budget_reason}",
                extra={
                    "worthiness_score": worthiness_score,
                    "estimated_cost_cents": estimated_cost_cents,
                    "usage_info": usage_info,
                },
            )
            return (
                False,
                budget_reason,
                {
                    "worthiness_score": worthiness_score,
                    "estimated_cost_cents": estimated_cost_cents,
                    "usage_info": usage_info,
                    "could_be_enhanced": True,  # Flag to indicate this could have been enhanced
                    "triggered_rewards": [],  # No rewards when budget blocked
                },
            )

        # Value-first decision logic
        should_enhance = False
        decision_reason = ""

        if worthiness_score >= EXCEPTIONAL_THRESHOLD:
            # Exceptional content always gets AI if budget allows
            should_enhance = True
            decision_reason = f"Exceptional worthiness ({worthiness_score:.3f} >= {EXCEPTIONAL_THRESHOLD})"

        elif worthiness_score >= GOOD_THRESHOLD:
            # Good content gets probabilistic enhancement based on worthiness
            # Higher worthiness = higher probability
            probability = (worthiness_score - GOOD_THRESHOLD) / (
                EXCEPTIONAL_THRESHOLD - GOOD_THRESHOLD
            )
            probability = min(probability * 1.5, 1.0)  # Boost probability slightly

            import random

            random_value = random.random()
            should_enhance = random_value < probability

            decision_reason = (
                f"Good worthiness ({worthiness_score:.3f}), "
                f"probability={probability:.3f}, random={random_value:.3f}"
            )
        else:
            # Low worthiness content rarely gets AI
            decision_reason = (
                f"Low worthiness ({worthiness_score:.3f} < {GOOD_THRESHOLD})"
            )
            should_enhance = False

        # Track the selection decision using new tracking service
        pulse_id = pulse_data.get("pulse_id", "unknown")
        tracking_integration.track_selection_decision(
            user_id=user_id,
            pulse_id=pulse_id,
            worthiness_score=worthiness_score,
            decision=decision_reason,
            ai_worthy=should_enhance,
            estimated_cost_cents=estimated_cost_cents,
            metadata={
                "budget_available": can_afford,
                "model_id": config.get("bedrock_model_id"),
            }
        )

        # Check for rewards without recording enhancement (will be recorded in Bedrock handler)
        # Only pre-calculate rewards if we're actually going to enhance
        triggered_rewards = []
        if should_enhance:
            # Pre-calculate rewards based on pulse data without incrementing counters
            triggered_rewards = budget_service._check_rewards_and_achievements(
                budget_service.get_or_create_daily_usage(user_id), pulse_data
            )

        logger.info(
            f"AI selection decision for user {user_id}: {decision_reason}, enhance={should_enhance}",
            extra={
                "worthiness_score": worthiness_score,
                "estimated_cost_cents": estimated_cost_cents,
                "can_afford": can_afford,
                "should_enhance": should_enhance,
                "decision_reason": decision_reason,
                "triggered_rewards": len(triggered_rewards) if triggered_rewards else 0,
            },
        )

        return (
            should_enhance,
            decision_reason,
            {
                "worthiness_score": worthiness_score,
                "estimated_cost_cents": estimated_cost_cents,
                "usage_info": usage_info,
                "triggered_rewards": triggered_rewards,
                "could_be_enhanced": True,  # Budget available, just worthiness decision
            },
        )

    except Exception as e:
        logger.error(f"Error in AI selection logic: {e}")
        return False, f"Error in selection: {str(e)}", {}


@logger.inject_lambda_context
def ai_selection_handler(event, context: LambdaContext):
    """
    Lambda function handler for AI selection using Powertools.

    Input: List of DynamoDB stream records from EventBridge Pipes or DynamoDB stream event
    Output: Event with aiWorthy flag added and pulseData extracted
    """
    logger.info(
        "AI Selection Lambda invoked", extra={"event_type": type(event).__name__}
    )

    try:
        # Get AI configuration
        config = get_ai_config()
        logger.info("Retrieved AI configuration", extra={"config": config})

        # Parse event using Powertools
        ddb_event = parse_event(event)  # type: ignore

        # Convert iterator to list to get count and access records
        records_list = list(ddb_event.records)
        logger.info(f"Parsed {len(records_list)} DynamoDB records")

        # EventBridge Pipes with batchSize=1 sends exactly one record
        if len(records_list) != 1:
            raise ValueError(
                f"Expected exactly 1 DynamoDB record, got {len(records_list)}"
            )

        # Process the single record
        record = records_list[0]
        pulse_data = extract_pulse_data_from_record(record)
        processed_record = record

        if not pulse_data:
            logger.error("No valid pulse data found in any record")
            return {
                "aiWorthy": False,
                "error": "No pulse data found",
                "originalEvent": event,
            }

        # Extract pulse ID and user ID for logging (pulse_data is already in Python format)
        pulse_id = pulse_data.get("pulse_id", "unknown")
        user_id = pulse_data.get("user_id", "unknown")
        logger.info(
            f"Processing pulse {pulse_id} for user {user_id} from record {processed_record.event_id}"
        )

        # Determine if AI enhancement should be applied using value-first approach
        ai_worthy, decision_reason, selection_info = should_enhance_with_ai(
            pulse_data, config, user_id
        )

        # Return structured result for Step Functions
        result: Dict[str, Any] = {
            "aiWorthy": ai_worthy,
            "aiConfig": config,
            "pulseData": pulse_data,
            "originalEvent": event,
            "selectionInfo": {
                "decision_reason": decision_reason,
                "worthiness_score": selection_info.get("worthiness_score", 0),
                "estimated_cost_cents": selection_info.get("estimated_cost_cents", 0),
                "usage_info": selection_info.get("usage_info", {}),
            },
            "triggeredRewards": selection_info.get("triggered_rewards", []),
            "recordInfo": {
                "eventId": processed_record.event_id,
                "eventName": str(processed_record.event_name),
                "pulseId": pulse_id,
                "userId": user_id,
            },
        }

        logger.info(
            "AI selection completed",
            extra={
                "pulse_id": pulse_id,
                "ai_worthy": ai_worthy,
                "event_id": processed_record.event_id,
            },  # type: ignore
        )
        return result

    except Exception as e:
        logger.exception("Error in AI selection")
        return {"aiWorthy": False, "error": str(e), "originalEvent": event}  # type: ignore


# Wrap with tracking
handler = app_with_tracking(ai_selection_handler, tracking_integration)
