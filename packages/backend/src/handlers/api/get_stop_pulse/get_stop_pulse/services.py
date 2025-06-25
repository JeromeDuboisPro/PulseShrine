import logging

from shared.models.pulse import StopPulse
from shared.services.aws import get_ddb_table
from botocore.exceptions import BotoCoreError, ClientError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)


def get_stop_pulses(
    user_id: str,
    table_name: str,
) -> list[StopPulse]:
    """
    Delete a pulse for the given user by removing it from the DynamoDB table.
    Args:
        user_id (str): ID of the user whose pulse is to be deleted.
        table_name (str): Name of the DynamoDB table.
    Returns:
        bool: True if the pulse was successfully deleted, False otherwise.
    """
    try:
        response = get_ddb_table(table_name).query(
            IndexName="UserIdIndex", KeyConditionExpression=Key("user_id").eq(user_id)
        )

        return [StopPulse(**item) for item in response["Items"]]

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
