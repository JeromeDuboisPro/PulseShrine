import random
import os
from decimal import Decimal
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

# Initialize the logger
logger = Logger()

# Initialize SSM client
ssm_client = boto3.client("ssm")

# Cache for parameters to reduce API calls
parameter_cache = {}


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
        "target_percentage": float(get_parameter(f"{prefix}target_percentage", "0.10")),
        "duration_weight": float(get_parameter(f"{prefix}duration_weight", "0.4")),
        "reflection_weight": float(get_parameter(f"{prefix}reflection_weight", "0.3")),
        "intent_weight": float(get_parameter(f"{prefix}intent_weight", "0.2")),
        "max_cost_cents": float(
            get_parameter(f"{prefix}max_cost_per_pulse_cents", "2")
        ),
        "enabled": get_parameter(f"{prefix}enabled", "true").lower() == "true",
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


def calculate_ai_worthiness_score(
    pulse_data: Dict[str, Any], config: Dict[str, float]
) -> float:
    """Calculate AI worthiness score based on pulse characteristics"""
    score = 0.0

    try:
        # Extract values from DynamoDB format using Powertools utilities
        # Extract values directly from Python-formatted pulse data
        duration_seconds = pulse_data.get("duration_seconds", 0)
        reflection = pulse_data.get("reflection", "")
        intent = pulse_data.get("intent", "")
        intent_emotion = pulse_data.get("intent_emotion", "")
        reflection_emotion = pulse_data.get("reflection_emotion", "")

        # Convert to appropriate types (handle Decimal from DynamoDB)
        duration_seconds = float(duration_seconds) if duration_seconds is not None else 0
        reflection = str(reflection) if reflection is not None else ""
        intent = str(intent) if intent is not None else ""

        # Duration-based scoring (longer sessions = higher value)
        if duration_seconds > 3600:  # 1+ hour
            score += config["duration_weight"] * 1.0
        elif duration_seconds > 1800:  # 30+ min
            score += config["duration_weight"] * 0.6
        elif duration_seconds > 900:  # 15+ min
            score += config["duration_weight"] * 0.3

        # Reflection quality scoring (detailed reflections = higher value)
        word_count = len(reflection.split()) if reflection else 0
        if word_count > 50:
            score += config["reflection_weight"] * 1.0
        elif word_count > 20:
            score += config["reflection_weight"] * 0.6
        elif word_count > 10:
            score += config["reflection_weight"] * 0.3

        # Intent-based scoring (work/study intentions = higher ROI)
        high_value_intents = [
            "focus",
            "creation",
            "study",
            "work",
            "coding",
            "planning",
        ]
        intent_lower = intent.lower()
        intent_emotion_lower = str(intent_emotion).lower() if intent_emotion else ""

        if any(
            keyword in intent_lower or keyword in intent_emotion_lower
            for keyword in high_value_intents
        ):
            score += config["intent_weight"] * 1.0
        elif any(
            keyword in intent_lower
            for keyword in ["brainstorm", "creative", "learning"]
        ):
            score += config["intent_weight"] * 0.6

        # Emotion complexity bonus (mixed emotions = AI adds more value)
        if reflection_emotion and str(reflection_emotion).lower() in [
            "mixed",
            "complex",
            "conflicted",
        ]:
            score += 0.1

        logger.info(
            "AI worthiness calculation completed",
            extra={
                "duration_seconds": duration_seconds,
                "reflection_words": word_count,
                "intent": intent,
                "intent_emotion": intent_emotion,
                "reflection_emotion": reflection_emotion,
                "worthiness_score": score,
            },
        )

        return min(
            score, config["target_percentage"] * 1.5
        )  # Cap at 1.5x target to allow headroom

    except Exception as e:
        logger.error(f"Error calculating AI worthiness: {e}")
        return 0.0


def should_enhance_with_ai(
    pulse_data: Dict[str, Any], config: Dict[str, float]
) -> bool:
    """Determine if pulse should be enhanced with AI"""

    if not config["enabled"]:
        logger.info("AI enhancement is disabled")
        return False

    # Calculate worthiness score
    worthiness_score = calculate_ai_worthiness_score(pulse_data, config)

    # Use random selection with weighted probability
    random_value = random.random()
    should_enhance = random_value < worthiness_score

    logger.info(
        f"AI selection decision: worthiness={worthiness_score:.3f}, "
        f"random={random_value:.3f}, enhance={should_enhance}"
    )

    return should_enhance


@logger.inject_lambda_context
def handler(event, context: LambdaContext):
    """
    Lambda function handler for AI selection using Powertools.

    Input: List of DynamoDB stream records from EventBridge Pipes or DynamoDB stream event
    Output: Event with aiWorthy flag added and pulseData extracted
    """
    logger.info(
        f"AI Selection Lambda invoked", extra={"event_type": type(event).__name__}
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

        # Extract pulse ID for logging (pulse_data is already in Python format)
        pulse_id = pulse_data.get("pulse_id", "unknown")
        logger.info(
            f"Processing pulse {pulse_id} from record {processed_record.event_id}"
        )

        # Determine if AI enhancement should be applied
        ai_worthy = should_enhance_with_ai(pulse_data, config)

        # Return structured result for Step Functions
        result: Dict[str, Any] = {
            "aiWorthy": ai_worthy,
            "aiConfig": config,
            "pulseData": pulse_data,
            "originalEvent": event,
            "recordInfo": {
                "eventId": processed_record.event_id,
                "eventName": str(processed_record.event_name),
                "pulseId": pulse_id,
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
