import datetime
import logging
import uuid
from decimal import Decimal
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from src.shared.models.pulse import PulseCreationError
from src.shared.services.aws import get_ddb_table

logger = logging.getLogger(__name__)


def get_start_pulse_table_name() -> str:
    """
    Retrieve the name of the DynamoDB table used for storing pulses.

    Returns:
        str: The name of the DynamoDB table.
    """
    return "StartPulsesTable"  # Replace with your actual table name or configuration retrieval logic


def get_ingest_pulse_table_name() -> str:
    """
    Retrieve the name of the DynamoDB table used for storing pulses.

    Returns:
        str: The name of the DynamoDB table.
    """
    return "IngestPulsesTable"  # Replace with your actual table name or configuration retrieval logic


# Initialize DynamoDB resource


def start_pulse(
    user_id: str,
    start_time: datetime.datetime,
    intent: str,
    table_name: str,
    pulse_id: str | None = None,
    duration_seconds: int | None = None,
    tags: list[str] | None = None,
    is_public: bool = False,
) -> str:
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
        pulse_id = pulse_id or str(uuid.uuid4())

        # Convert datetime to ISO format string for DynamoDB
        start_time_iso = start_time.isoformat()
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Prepare the item to insert
        item: dict[str, str | bool | Decimal | list[str]] = {
            "pulse_id": pulse_id,
            "user_id": user_id,
            "start_time": start_time_iso,
            "intent": intent,
            "is_public": is_public,
            "created_at": created_at,
            "updated_at": created_at,
        }

        # Add optional fields if provided
        if duration_seconds is not None:
            # Convert to Decimal for DynamoDB compatibility
            item["duration_seconds"] = Decimal(str(duration_seconds))

        if tags:
            item["tags"] = tags

        # Calculate end_time if duration is provided
        if duration_seconds is not None:
            from datetime import timedelta

            end_time = start_time + timedelta(seconds=duration_seconds)
            item["end_time"] = end_time.isoformat()

        # Put item into DynamoDB
        get_ddb_table(table_name).put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(pulse_id)",  # Prevent overwrites
        )

        logger.info(f"Successfully created pulse {pulse_id} for user {user_id}")
        return pulse_id

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]

        if error_code == "ConditionalCheckFailedException":
            raise PulseCreationError(f"Pulse with ID {pulse_id} already exists")
        elif error_code == "ResourceNotFoundException":
            raise PulseCreationError(f"Table {table_name} does not exist")
        else:
            raise PulseCreationError(f"DynamoDB error: {error_code} - {error_message}")

    except BotoCoreError as e:
        raise PulseCreationError(f"AWS connection error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error creating pulse: {str(e)}")
        raise PulseCreationError(f"Failed to create pulse: {str(e)}")


def _delete_pulse(
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
    pulse: Any,
    reflection: str,
    stopped_at: datetime.datetime,
    stop_pulse_table_name: str,
) -> dict | None:
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
        **pulse,
        "reflection": reflection,
        "stopped_at": stopped_at.isoformat(),
        "pulse_id": pulse.get("pulse_id", str(uuid.uuid4())),  # Ensure pulse_id is set
        "user_id": pulse.get("user_id", "unknown_user"),  # Ensure user_id is set
    }
    try:
        get_ddb_table(stop_pulse_table_name).put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(pulse_id)",  # Prevent overwrites
        )
        logger.info(f"Successfully sent pulse {item['pulse_id']} to ingestion")
        return item
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


def stop_pulse(
    user_id: str,
    start_pulse_table_name: str,
    stop_pulse_table_name: str,
    reflection: str,
    stopped_at: datetime.datetime,
) -> Any:
    """
    Stop a pulse for the given user by removing it from the DynamoDB table.

    Args:
        user_id (str): ID of the user whose pulse is to be stopped.
        table_name (str): Name of the DynamoDB table.

    Returns:
        bool: True if the pulse was successfully stopped, False otherwise.
    """

    response = _delete_pulse(
        user_id=user_id,
        table_name=start_pulse_table_name,
    )

    _pulse = response.get("Attributes", None)
    if not _pulse:
        logger.warning(f"No pulse found for user {user_id} to stop")
        return None

    logger.info(f"Pulse stopped for user {user_id}: {_pulse}")
    ingest_pulse = _send_pulse_to_ingestion(
        pulse=_pulse,
        reflection=reflection,
        stopped_at=stopped_at,
        stop_pulse_table_name=stop_pulse_table_name,
    )
    return ingest_pulse


def get_start_pulse(user_id: str, table_name: str) -> dict | None:
    """
    Retrieve a pulse by its ID from the DynamoDB table.

    Args:
        pulse_id (str): The ID of the pulse to retrieve.

    Returns:
        dict: The pulse item if found, otherwise None.
    """
    try:
        response = get_ddb_table(table_name).get_item(Key={"user_id": user_id})
        return response.get("Item", None)

    except ClientError as e:
        logger.error(
            f"Error retrieving pulse for user {user_id}: {e.response['Error']['Message']}"
        )
        return None
    except BotoCoreError as e:
        logger.error(f"AWS connection error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving pulse for user {user_id}: {str(e)}")
        return None
