import datetime
from decimal import Decimal
from typing import Any
import uuid
from shared.models.pulse import PulseCreationError, StartPulse, StopPulse
from shared.services.aws import get_ddb_table
from botocore.exceptions import BotoCoreError, ClientError
from models import PulseCreationErrorAlreadyPresent
import logging

logger = logging.getLogger(__name__)


def _delete_start_pulse(
    user_id: str,
    table_name: str,
) -> Any:
    """
    Delete a pulse for the given user by removing it from the DynamoDB table.
    Args:
        user_id (str): ID of the user whose pulse is to be deleted.
        table_name (str): Name of the DynamoDB table.
    Returns:
        bool: True if the pulse was successfully deleted, False otherwise.
    """
    try:
        response = get_ddb_table(table_name).delete_item(
            Key={"user_id": user_id}, ReturnValues="ALL_OLD"
        )

        if "Attributes" in response:
            logger.info(f"Successfully deleted pulse for user {user_id}")
            return response
        else:
            logger.warning(f"No pulse found for user {user_id} to delete")

    except ClientError as e:
        logger.error(
            f"Error deleting pulse for user {user_id}: {e.response['Error']['Message']}"
        )
    except BotoCoreError as e:
        logger.error(f"AWS connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error deleting pulse for user {user_id}: {str(e)}")
    return None


def _send_pulse_to_ingestion(
    stop_pulse: StopPulse,
    stop_pulse_table_name: str,
) -> StopPulse | None:
    """
    Send a pulse to the ingestion service by stopping it and returning the pulse data.

    Args:
        user_id (str): ID of the user whose pulse is to be sent.
        start_pulse_table_name (str): Name of the DynamoDB table for starting pulses.
        stop_pulse_table_name (str): Name of the DynamoDB table for stopping pulses.

    Returns:
        dict: The pulse data if successfully stopped, otherwise None.
    """
    # Put item into DynamoDB
    item = {
        **stop_pulse.model_dump(),
    }

    try:
        get_ddb_table(stop_pulse_table_name).put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(pulse_id)",  # Prevent overwrites
        )
        logger.info(f"Successfully sent pulse {item['pulse_id']} to ingestion")
        return stop_pulse
    except ClientError as e:
        logger.error(
            f"Error sending pulse {item['pulse_id']} to ingestion: {e.response['Error']['Message']}"
        )
    except BotoCoreError as e:
        logger.error(f"AWS connection error: {str(e)}")
    except Exception as e:
        logger.error(
            f"Unexpected error sending pulse {item['pulse_id']} to ingestion: {str(e)}"
        )
    return None


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

        # Convert datetime to ISO format string for DynamoDB
        start_time_iso = pulse_data.start_time_dt.isoformat()
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

        if pulse_data.tags:
            item["tags"] = pulse_data.tags

        # Calculate end_time if duration is provided
        if pulse_data.duration_seconds is not None:
            from datetime import timedelta

            end_time = pulse_data.start_time_dt + timedelta(
                seconds=pulse_data.duration_seconds
            )
            item["end_time"] = end_time.isoformat()

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


def stop_pulse(
    user_id: str,
    start_pulse_table_name: str,
    stop_pulse_table_name: str,
    reflection: str,
    stopped_at: datetime.datetime,
) -> StopPulse | None:
    """
    Stop a pulse for the given user by removing it from the DynamoDB table.

    Args:
        user_id (str): ID of the user whose pulse is to be stopped.
        table_name (str): Name of the DynamoDB table.

    Returns:
        bool: True if the pulse was successfully stopped, False otherwise.
    """

    response = _delete_start_pulse(
        user_id=user_id,
        table_name=start_pulse_table_name,
    )

    _pulse = response.get("Attributes", None)
    if not _pulse:
        logger.warning(f"No pulse found for user {user_id} to stop")
        return None

    logger.info(f"Pulse stopped for user {user_id}: {_pulse}")
    stop_pulse = StopPulse(
        user_id=user_id,
        pulse_id=_pulse["pulse_id"],
        start_time=_pulse["start_time"],
        intent=_pulse["intent"],
        reflection=reflection,
        stopped_at=stopped_at.isoformat(),
        duration_seconds=_pulse.get("duration_seconds"),
        tags=_pulse.get("tags"),
        is_public=_pulse.get("is_public", False),
    )
    stop_pulse = _send_pulse_to_ingestion(
        stop_pulse=stop_pulse,
        stop_pulse_table_name=stop_pulse_table_name,
    )

    return stop_pulse
