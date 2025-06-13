import json
import os
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.batch import (BatchProcessor, EventType,
                                                   process_partial_response)
from aws_lambda_powertools.utilities.batch.types import \
    PartialItemFailureResponse
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.types import TypeDeserializer
from typing import Any, Dict

from shared.models.pulse import StopPulse
from shared.services.pulse import ingest_pulse

# Initialize Powertools utilities
logger = Logger()
tracer = Tracer()
processor = BatchProcessor(event_type=EventType.SQS)
deserializer = TypeDeserializer()

# Environment variables
SQS_QUEUE_ARN = os.environ["SQS_QUEUE_ARN"]
STOP_PULSE_TABLE_NAME = os.environ["STOP_PULSE_TABLE_NAME"]
INGESTED_PULSE_TABLE_NAME = os.environ["INGESTED_PULSE_TABLE_NAME"]


@tracer.capture_lambda_handler
@logger.inject_lambda_context
def handler(
    event: Dict[str, Any], context: LambdaContext
) -> PartialItemFailureResponse:
    logger.info(
        f"Processing {len(event.get('Records', []))} SQS messages containing DynamoDB stream events"
    )

    return process_partial_response(
        event=event,
        record_handler=record_handler,
        processor=processor,
        context=context,
    )


class InvalidPayload(Exception):
    """Custom exception for invalid SQS message payload containing DynamoDB stream data."""

    pass


def deserialize_dynamodb_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize DynamoDB item from DynamoDB JSON format to Python dict.

    Args:
        item: DynamoDB item in DynamoDB JSON format

    Returns:
        Deserialized Python dictionary
    """
    try:
        return {key: deserializer.deserialize(value) for key, value in item.items()}
    except Exception as e:
        logger.error(f"Failed to deserialize DynamoDB item", exc_info=e)
        raise InvalidPayload(f"Failed to deserialize DynamoDB item: {str(e)}")


def parse_dynamodb_stream_event(sqs_body: str) -> Dict[str, Any]:
    """
    Parse DynamoDB stream event from SQS message body.

    Args:
        sqs_body: JSON string containing DynamoDB stream event

    Returns:
        Parsed DynamoDB stream event dictionary

    Raises:
        InvalidPayload: If parsing fails or required fields are missing
    """
    try:
        stream_event = json.loads(sqs_body)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from SQS message body", exc_info=e)
        raise InvalidPayload(f"Invalid JSON format in SQS message body: {str(e)}")

    # Validate DynamoDB stream event structure
    if not isinstance(stream_event, dict):
        raise InvalidPayload("SQS message body is not a valid JSON object")

    if (
        "eventSource" not in stream_event
        or stream_event["eventSource"] != "aws:dynamodb"
    ):
        raise InvalidPayload("SQS message does not contain a DynamoDB stream event")

    if "eventName" not in stream_event:
        raise InvalidPayload("DynamoDB stream event missing eventName")

    if "dynamodb" not in stream_event:
        raise InvalidPayload("DynamoDB stream event missing dynamodb data")

    return stream_event


def validate_dynamodb_event(stream_event: Dict[str, Any]) -> None:
    """
    Validate DynamoDB stream event structure and content.

    Args:
        stream_event: Parsed DynamoDB stream event

    Raises:
        InvalidPayload: If event is invalid or unsupported
    """
    event_name = stream_event.get("eventName")

    # Only process INSERT and MODIFY events (events with NewImage)
    if event_name not in ["INSERT", "MODIFY"]:
        logger.info(f"Skipping unsupported event type: {event_name}")
        raise InvalidPayload(f"Unsupported event type: {event_name}")

    dynamodb_data = stream_event.get("dynamodb", {})

    # Check for NewImage
    if "NewImage" not in dynamodb_data:
        raise InvalidPayload("DynamoDB stream event missing NewImage data")

    # Validate required pulse_id field
    new_image = dynamodb_data["NewImage"]
    if "pulse_id" not in new_image:
        raise InvalidPayload("Missing required field 'pulse_id' in NewImage")


@tracer.capture_method
def record_handler(record: SQSRecord) -> None:
    """
    Handle individual SQS record containing DynamoDB stream event.

    Args:
        record: SQS record containing DynamoDB stream event in body

    Raises:
        InvalidPayload: For invalid record structure or data
        ValueError: For data validation errors
        Exception: For unexpected processing errors
    """
    logger.info(f"Processing SQS message ID: {record.message_id}")

    try:
        # Parse DynamoDB stream event from SQS message body
        stream_event = parse_dynamodb_stream_event(record.body)

        # Log event details
        event_name = stream_event.get("eventName")
        event_source = stream_event.get("eventSource")
        logger.info(
            f"Processing DynamoDB stream event - Event: {event_name}, Source: {event_source}"
        )

        # Validate the event
        validate_dynamodb_event(stream_event)

        # Extract and deserialize NewImage data
        new_image_raw = stream_event["dynamodb"]["NewImage"]
        pulse_data = deserialize_dynamodb_item(new_image_raw)
        print(f"pulse_data: {pulse_data}")
        stop_pulse = StopPulse(**pulse_data)
        pulse_id = pulse_data["pulse_id"]
        logger.info(f"Processing pulse with ID: {pulse_id}")

        # Add stream event metadata to pulse data for context
        pulse_data["_stream_metadata"] = {
            "event_id": stream_event.get("eventID"),
            "event_name": event_name,
            "event_source": event_source,
            "aws_region": stream_event.get("awsRegion"),
            "event_source_arn": stream_event.get("eventSourceARN"),
            "approximate_creation_time": stream_event["dynamodb"].get(
                "ApproximateCreationDateTime"
            ),
        }

        # Process the pulse
        ingest_pulse(
            stop_pulse=stop_pulse,
            stop_pulse_table_name=STOP_PULSE_TABLE_NAME,
            ingested_pulse_table_name=INGESTED_PULSE_TABLE_NAME,
        )

        logger.info(f"Successfully processed pulse: {pulse_id}")

    except InvalidPayload as e:
        logger.error(
            f"Invalid SQS message payload: {str(e)}",
            extra={
                "message_id": record.message_id,
                "receipt_handle": record.receipt_handle,
            },
        )
        raise

    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to decode JSON from SQS message body",
            extra={"message_id": record.message_id},
            exc_info=e,
        )
        raise InvalidPayload(f"Invalid JSON format in SQS message body: {str(e)}")

    except KeyError as e:
        logger.error(
            f"Missing required field in pulse data: {str(e)}",
            extra={"message_id": record.message_id},
        )
        raise InvalidPayload(f"Missing required field: {str(e)}")

    except ValueError as e:
        logger.error(
            f"Value error processing pulse data: {str(e)}",
            extra={"message_id": record.message_id},
        )
        raise

    except TypeError as e:
        logger.error(
            f"Type error processing pulse data: {str(e)}",
            extra={"message_id": record.message_id},
        )
        raise ValueError(f"Type error in pulse data: {str(e)}")

    except Exception as e:
        logger.error(
            f"Unexpected error processing SQS message: {str(e)}",
            extra={"message_id": record.message_id},
            exc_info=True,
        )
        raise
