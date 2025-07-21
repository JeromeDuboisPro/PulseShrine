import os
from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, UnauthorizedError
from aws_lambda_powertools.utilities.typing import LambdaContext
from typing import Any

from shared.models.pulse import StopPulse
from shared.utils.auth import extract_user_id_from_event
from get_stop_pulse.services import get_stop_pulses

# Initialize the logger
logger = Logger()

# Retrieve environment variable
STOP_PULSE_TABLE_NAME = os.environ["STOP_PULSE_TABLE_NAME"]

# Configure CORS
cors_config = CORSConfig(
    allow_origin="*",  # In production, specify your actual domain
)

# Initialize the APIGatewayRestResolver
app = APIGatewayRestResolver(cors=cors_config)


@app.get("/get-stop-pulses")
def get_stop_pulses_handler() -> list[StopPulse]:
    """
    Handler function to get the stop pulses of a user.
    Extracts user_id from JWT token in the request context.
    """
    # Extract user_id from JWT token
    user_id = extract_user_id_from_event(app.current_event.raw_event)
    if not user_id:
        logger.error("No user_id found in JWT token")
        raise UnauthorizedError("Authentication required")
    
    logger.info(f"Retrieving current StopPulses for user {user_id}")

    try:
        results = list(
            get_stop_pulses(user_id=user_id, table_name=STOP_PULSE_TABLE_NAME)
        )
        print(f"For user {user_id} got the following StopPulses: {results}")
        return results

    except Exception as exc:
        logger.error(f"Unexpected error: {str(exc)}")
        raise BadRequestError("An unexpected error occurred while retrieving pulses.")


def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Lambda function handler.
    """
    logger.info(f"Type of event: {type(event)}")
    logger.info(f"Received event: {event}")

    return app.resolve(event, context)
