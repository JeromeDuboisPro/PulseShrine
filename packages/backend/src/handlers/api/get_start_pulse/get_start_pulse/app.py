import os
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, UnauthorizedError
from aws_lambda_powertools.utilities.typing import LambdaContext
from typing import Any
from datetime import datetime, timezone

from shared.utils.auth import extract_user_id_from_event
from get_start_pulse.services import get_start_pulse

# Initialize the logger
logger = Logger()

# Retrieve environment variable
START_PULSE_TABLE_NAME = os.environ["START_PULSE_TABLE_NAME"]

# Configure CORS
cors_config = CORSConfig(
    allow_origin="*",  # In production, specify your actual domain
)

# Initialize the APIGatewayRestResolver
app = APIGatewayRestResolver(cors=cors_config)


@app.get("/get-start-pulse")
def get_start_pulse_handler() -> dict[str, Any] | None:
    """
    Handler function to get the start pulse of a user.
    Extracts user_id from JWT token in the request context.
    """
    # Extract user_id from JWT token
    user_id = extract_user_id_from_event(app.current_event.raw_event)
    if not user_id:
        logger.error("No user_id found in JWT token")
        raise UnauthorizedError("Authentication required")
    
    logger.info(f"Retrieving current StartPulse for user {user_id}")
    try:
        result = get_start_pulse(user_id=user_id, table_name=START_PULSE_TABLE_NAME)
        if result:
            # Custom serialization to preserve timezone info
            data = result.model_dump(mode="json")
            # Ensure start_time includes timezone info
            if hasattr(result, "start_time_dt") and result.start_time_dt:
                data["start_time"] = result.start_time_dt.isoformat()
            
            # Calculate remaining time on the server
            current_time = datetime.now(timezone.utc)
            elapsed_seconds = (current_time - result.start_time_dt).total_seconds()
            remaining_seconds = max(0, result.duration_seconds - elapsed_seconds)
            data["remaining_seconds"] = int(remaining_seconds)
            data["server_time"] = current_time.isoformat()
            logger.info(f"Calculated remaining time: {remaining_seconds}s for user {user_id}")
            
            return data
        return None

    except Exception as exc:
        logger.error(f"Unexpected error: {str(exc)}")
        raise BadRequestError("An unexpected error occurred while retrieving the pulse.")


def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Lambda function handler.
    """
    logger.info(f"Type of event: {type(event)}")
    logger.info(f"Received event: {event}")

    return app.resolve(event, context)
