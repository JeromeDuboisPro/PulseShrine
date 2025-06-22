import datetime
from typing import Any
from models import (
    PulseDDBIngestionError,
)
from shared.models.pulse import StopPulse, ArchivedPulse
from generators import PulseTitleGenerator
import logging

from shared.services.aws import get_ddb_table
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


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
        **stop_pulse.model_dump(),
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
