import logging
from decimal import Decimal

from shared.models.pulse import ArchivedPulse
from shared.services.aws import get_ddb_table
from botocore.exceptions import BotoCoreError, ClientError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

DEFAULT_NB_ITEMS = 20
MAX_NB_ITEMS = 100


def convert_decimals_to_float(obj):
    """Recursively convert Decimal values to float for API compatibility"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    else:
        return obj


def get_ingested_pulses(
    user_id: str,
    table_name: str,
    nb_items: int = DEFAULT_NB_ITEMS,
) -> list[ArchivedPulse]:
    """
    Delete a pulse for the given user by removing it from the DynamoDB table.
    Args:
        user_id (str): ID of the user whose pulse is to be deleted.
        table_name (str): Name of the DynamoDB table.
    Returns:
        bool: True if the pulse was successfully deleted, False otherwise.
    """
    nb_items = min(MAX_NB_ITEMS, nb_items)
    try:
        response = get_ddb_table(table_name).query(
            IndexName="UserIdStoppedAtIndex",
            KeyConditionExpression=Key("user_id").eq(user_id),
            ScanIndexForward=True,
            Limit=nb_items,
        )

        # Convert Decimals to floats before creating ArchivedPulse objects
        items = [convert_decimals_to_float(item) for item in response["Items"]]
        return [ArchivedPulse(**item) for item in items]

    except ClientError as e:
        logger.error(
            f"Error getting stop pulses for user {user_id}: {e.response['Error']['Message']}"
        )
    except BotoCoreError as e:
        logger.error(f"AWS connection error: {str(e)}")
    except Exception as e:
        logger.error(
            f"Unexpected error getting stop pulses for user {user_id}: {str(e)}"
        )
    return []
