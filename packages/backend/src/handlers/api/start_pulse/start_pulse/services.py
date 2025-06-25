import datetime
from decimal import Decimal
import uuid
from shared.models.pulse import PulseCreationError, StartPulse
from shared.services.aws import get_ddb_table
from botocore.exceptions import BotoCoreError, ClientError
from start_pulse.models import PulseCreationErrorAlreadyPresent
import logging

logger = logging.getLogger(__name__)


def start_pulse(
    pulse_data: StartPulse,
    table_name: str,
) -> StartPulse:
    """
    Create a new pulse with the given parameters and store it in the provided DynamoDB table.

    Args:
        user_id (str): ID of the user creating the pulse.
        start_time (datetime): Start time of the pulse.
        intent (str): Intent or title of the pulse.
        duration_seconds (int, optional): Duration of the pulse.
        tags (list[str], optional): List of tags associated with the pulse.
        is_public (bool, optional): Whether the pulse is public.
        table: DynamoDB table resource to store the pulse.

    Returns:
        str: id of the newly created start_pulse.
    """
    try:
        # Generate unique pulse ID
        pulse_data.pulse_id = pulse_data.pulse_id or str(uuid.uuid4())

        # Convert datetime to UTC ISO format string for DynamoDB
        if pulse_data.start_time_dt.tzinfo is None:
            # If naive datetime, assume it's UTC
            start_time_utc = pulse_data.start_time_dt.replace(
                tzinfo=datetime.timezone.utc
            )
        else:
            # Convert to UTC if timezone-aware
            start_time_utc = pulse_data.start_time_dt.astimezone(datetime.timezone.utc)

        start_time_iso = start_time_utc.isoformat()
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Prepare the item to insert
        item: dict[str, str | bool | Decimal | list[str]] = {
            "pulse_id": pulse_data.pulse_id,
            "user_id": pulse_data.user_id,
            "start_time": start_time_iso,
            "intent": pulse_data.intent,
            "is_public": pulse_data.is_public,
            "created_at": created_at,
            "updated_at": created_at,
        }

        # Add optional fields if provided
        if pulse_data.duration_seconds is not None:
            # Convert to Decimal for DynamoDB compatibility
            item["duration_seconds"] = Decimal(str(pulse_data.duration_seconds))

        item["intent_emotion"] = pulse_data.intent_emotion or "neutral"

        if pulse_data.tags:
            item["tags"] = pulse_data.tags

        # Calculate end_time if duration is provided (always in UTC)
        if pulse_data.duration_seconds is not None:
            from datetime import timedelta

            end_time_utc = start_time_utc + timedelta(
                seconds=pulse_data.duration_seconds
            )
            item["end_time"] = end_time_utc.isoformat()

        # Put item into DynamoDB
        get_ddb_table(table_name).put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(pulse_id)",  # Prevent overwrites
        )

        logger.info(
            f"Successfully created pulse {pulse_data.pulse_id} for user {pulse_data.user_id}"
        )
        return pulse_data

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]

        if error_code == "ConditionalCheckFailedException":
            raise PulseCreationErrorAlreadyPresent(user_id=pulse_data.user_id) from e
        elif error_code == "ResourceNotFoundException":
            raise PulseCreationError(f"Table {table_name} does not exist")
        else:
            raise PulseCreationError(f"DynamoDB error: {error_code} - {error_message}")

    except BotoCoreError as e:
        raise PulseCreationError(f"AWS connection error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error creating pulse: {str(e)}")
        raise PulseCreationError(f"Failed to create pulse: {str(e)}")
