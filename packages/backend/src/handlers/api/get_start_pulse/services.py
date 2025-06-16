import logging

from shared.models.pulse import StartPulse
from shared.services.aws import get_ddb_table
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


def get_start_pulse(
    user_id: str,
    table_name: str,
) -> StartPulse | None:
    """
    Retrieve a StartPulse for the given user from the DynamoDB table.
    Args:
        user_id (str): ID of the user whose pulse is to be retrieved.
        table_name (str): Name of the DynamoDB table.
    Returns:
        StartPulse | None: The StartPulse object if found, otherwise None.
    """
    try:
        response = get_ddb_table(table_name).get_item(Key={"user_id": user_id})
        logger.debug(f"Response: {response}")
        item = response.get("Item")
        if item:
            logger.info(f"Successfully retrieved start pulse for user {user_id}")
            return StartPulse(**item)
        else:
            logger.info(f"No StartPulse found for user {user_id}")
    except ClientError as e:
        logger.error(
            f"Error retrieving pulse for user {user_id}: {e.response['Error']['Message']}"
        )
    except BotoCoreError as e:
        logger.error(f"AWS connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error retrieving pulse for user {user_id}: {str(e)}")
    return None
