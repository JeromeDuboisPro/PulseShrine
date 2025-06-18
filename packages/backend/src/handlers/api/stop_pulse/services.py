import datetime
from typing import Any
from shared.models.pulse import StopPulse
from shared.services.aws import get_ddb_table
from botocore.exceptions import BotoCoreError, ClientError
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
