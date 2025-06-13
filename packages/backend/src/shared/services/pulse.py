import datetime
import logging
import uuid
from botocore.exceptions import BotoCoreError, ClientError
from decimal import Decimal
from typing import Any

from shared.models.pulse import (ArchivedPulse, PulseCreationError,
                                 PulseCreationErrorAlreadyPresent,
                                 PulseDDBIngestionError, StartPulse, StopPulse)
from shared.services.aws import get_ddb_table
from shared.services.generators import PulseTitleGenerator

logger = logging.getLogger(__name__)


def get_start_pulse_table_name() -> str:
    """
    Retrieve the name of the DynamoDB table used for storing pulses.

    Returns:
        str: The name of the DynamoDB table.
    """
    return "StartPulsesTable"  # Replace with your actual table name or configuration retrieval logic


def get_stop_pulse_table_name() -> str:
    """
    Retrieve the name of the DynamoDB table used for storing pulses.

    Returns:
        str: The name of the DynamoDB table.
    """
    return "StopPulsesTable"  # Replace with your actual table name or configuration retrieval logic


def get_ingested_pulse_table_name() -> str:
    """
    Retrieve the name of the DynamoDB table used for storing pulses.

    Returns:
        str: The name of the DynamoDB table.
    """
    return "IngestedPulsesTable"  # Replace with your actual table name or configuration retrieval logic


# Initialize DynamoDB resource


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


def _delete_stop_pulse(
    pulse_id: str,
    table_name: str,
) -> Any | None:
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
            Key={"pulse_id": pulse_id}, ReturnValues="ALL_OLD"
        )

        if "Attributes" in response:
            logger.info(f"Successfully deleted pulse {pulse_id}")
            return response
        else:
            logger.warning(f"No pulse found for {pulse_id} to delete")

    except ClientError as e:
        logger.error(
            f"Error deleting pulse {pulse_id}: {e.response['Error']['Message']}"
        )
    except BotoCoreError as e:
        logger.error(f"AWS connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error deleting pulse {pulse_id}: {str(e)}")
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


def get_start_pulse(user_id: str, table_name: str) -> StartPulse | None:
    """
    Retrieve a pulse by its ID from the DynamoDB table.

    Args:
        pulse_id (str): The ID of the pulse to retrieve.

    Returns:
        dict: The pulse item if found, otherwise None.
    """
    try:
        response = get_ddb_table(table_name).get_item(Key={"user_id": user_id})
        item = response.get("Item")
        if not item:
            logger.warning(f"No pulse found for user {user_id}")
            return None
        return StartPulse(**item)

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


def get_stop_pulse(
    pulse_id: str,
    table_name: str,
) -> StopPulse | None:
    """
    Retrieve a pulse by its ID from the DynamoDB table.

    Args:
        pulse_id (str): The ID of the pulse to retrieve.
        table_name (str, optional): The name of the DynamoDB table. Defaults to None.

    Returns:
        dict: The pulse item if found, otherwise None.
    """
    try:
        response = get_ddb_table(table_name).get_item(Key={"pulse_id": pulse_id})
        item = response.get("Item")
        if not item:
            logger.warning(f"No pulse found with ID {pulse_id}")
            return None
        return StopPulse(**item)

    except ClientError as e:
        logger.error(
            f"Error retrieving pulse {pulse_id}: {e.response['Error']['Message']}"
        )
        return None
    except BotoCoreError as e:
        logger.error(f"AWS connection error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving pulse {pulse_id}: {str(e)}")
        return None


def _send_ingested_pulse_to_ingested_archive(
    archived_pulse: ArchivedPulse,
    ingested_pulse_table_name: str,
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
        **archived_pulse.model_dump(),
    }

    try:
        get_ddb_table(ingested_pulse_table_name).put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(pulse_id)",  # Prevent overwrites
        )
        logger.info(f"Successfully sent pulse {item['pulse_id']} to archives")
        return archived_pulse
    except ClientError as e:
        logger.error(
            f"Error sending pulse {item['pulse_id']} to archives: {e.response['Error']['Message']}"
        )
    except BotoCoreError as e:
        logger.error(f"AWS connection error: {str(e)}")
    except Exception as e:
        logger.error(
            f"Unexpected error sending pulse {item['pulse_id']} to archives: {str(e)}"
        )
    return None


def ingest_pulse(
    stop_pulse: StopPulse,
    stop_pulse_table_name: str,
    ingested_pulse_table_name: str,
) -> ArchivedPulse | None:
    """
    Ingest a pulse for the given user by stopping it and returning the pulse data.

    Args:
        user_id (str): ID of the user whose pulse is to be ingested.
        reflection (str): Reflection text associated with the pulse.
        stopped_at (datetime): Time when the pulse was stopped.

    Returns:
        dict: The pulse data if successfully ingested, otherwise None.
    """
    generated_title = PulseTitleGenerator.generate_title(stop_pulse)
    badge = PulseTitleGenerator.get_achievement_badge(stop_pulse)
    if not generated_title:
        logger.warning(
            f"Failed to generate title for pulse {stop_pulse.valid_pulse_id}"
        )
        return None
    logger.info(
        f"Generated title for pulse {stop_pulse.valid_pulse_id}: {generated_title}"
    )
    if not badge:
        logger.warning(
            f"Failed to generate badge for pulse {stop_pulse.valid_pulse_id}"
        )
        return None
    logger.info(f"Generated badge for pulse {stop_pulse.valid_pulse_id}: {badge}")
    # Store the ingested pulse in the ingested pulses table
    archived_pulse = ArchivedPulse(
        user_id=stop_pulse.user_id,
        pulse_id=stop_pulse.pulse_id,
        start_time=stop_pulse.start_time,
        intent=stop_pulse.intent,
        reflection=stop_pulse.reflection,
        stopped_at=stop_pulse.stopped_at,
        duration_seconds=stop_pulse.duration_seconds,
        tags=stop_pulse.tags,
        is_public=stop_pulse.is_public,
        archived_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        gen_title=generated_title,
        gen_badge=badge,
    )
    res_archived_pulse = _send_ingested_pulse_to_ingested_archive(
        archived_pulse=archived_pulse,
        ingested_pulse_table_name=ingested_pulse_table_name,
    )
    if res_archived_pulse is None:
        raise PulseDDBIngestionError("Sending StopPulse to Ingestion Table failed")
    res_delete_stop_pulse = _delete_stop_pulse(
        pulse_id=stop_pulse.valid_pulse_id,
        table_name=stop_pulse_table_name,
    )
    if res_delete_stop_pulse is None:
        raise PulseDDBIngestionError("Deleteing StopPulse from Stop Table failed")
    return archived_pulse
